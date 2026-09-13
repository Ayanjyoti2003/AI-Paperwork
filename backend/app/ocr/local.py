"""Paperwork Agent - Local OCR Provider.

Performs 100% offline, privacy-preserving optical character recognition using
RapidOCR (ONNX Runtime) with optional PyPDFium2 PDF page rendering.
Zero external network calls.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Optional

from app.ocr.base import (
    OCREngineUnavailableError,
    OCRLine,
    OCRPage,
    OCRProvider,
    OCRResult,
)

logger = logging.getLogger(__name__)


class LocalOCRProvider(OCRProvider):
    """Offline local OCR provider using RapidOCR and PyPDFium2."""

    def __init__(self) -> None:
        self._engine: Any = None
        self._engine_initialized = False

    @property
    def provider_name(self) -> str:
        return "local_ocr"

    def is_available(self) -> bool:
        """Check whether local OCR engine dependencies are installed."""
        try:
            import rapidocr_onnxruntime  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_engine(self) -> Any:
        """Lazily initialize the RapidOCR engine."""
        if not self._engine_initialized:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._engine = RapidOCR()
                self._engine_initialized = True
            except ImportError as e:
                raise OCREngineUnavailableError(
                    "Local OCR engine unavailable — install rapidocr-onnxruntime: "
                    "pip install rapidocr-onnxruntime"
                ) from e
            except Exception as e:
                raise OCREngineUnavailableError(
                    f"Failed to initialize local OCR engine: {e}"
                ) from e
        return self._engine

    def extract_text_from_image(self, image_bytes: bytes, page_number: int = 1) -> OCRPage:
        """Extract text from raw image bytes using RapidOCR."""
        engine = self._get_engine()
        try:
            result, _ = engine(image_bytes)
        except Exception as e:
            logger.error("Local OCR failed on image bytes (page %d)", page_number)
            raise OCREngineUnavailableError(f"Local OCR recognition failed: {e}") from e

        if not result:
            return OCRPage(page_number=page_number, text="", confidence=None, lines=[])

        # Parse detected boxes and text
        parsed = []
        for item in result:
            if len(item) >= 2 and item[1]:
                text_str = str(item[1]).strip()
                if not text_str:
                    continue
                conf = None
                if len(item) >= 3 and item[2] is not None:
                    try:
                        conf = float(item[2])
                    except (ValueError, TypeError):
                        pass
                box = item[0]
                y_min = min(pt[1] for pt in box)
                y_max = max(pt[1] for pt in box)
                y_center = (y_min + y_max) / 2.0
                x_min = min(pt[0] for pt in box)
                height = y_max - y_min
                parsed.append({
                    "text": text_str,
                    "confidence": conf,
                    "y_center": y_center,
                    "x_min": x_min,
                    "height": height,
                })

        if not parsed:
            return OCRPage(page_number=page_number, text="", confidence=None, lines=[])

        # Sort vertically by y_center
        parsed.sort(key=lambda p: p["y_center"])

        # Group boxes on the same line (vertical overlap)
        grouped_lines: list[list[dict]] = []
        current_line: list[dict] = [parsed[0]]

        for p in parsed[1:]:
            prev_y = current_line[-1]["y_center"]
            h = max(current_line[-1]["height"], p["height"], 10)
            if abs(p["y_center"] - prev_y) < h * 0.6:
                current_line.append(p)
            else:
                grouped_lines.append(current_line)
                current_line = [p]
        grouped_lines.append(current_line)

        lines: list[OCRLine] = []
        all_confidences: list[float] = []

        for line_items in grouped_lines:
            # Sort items horizontally from left to right
            line_items.sort(key=lambda p: p["x_min"])
            combined_line_text = " ".join(p["text"] for p in line_items)
            line_confs = [p["confidence"] for p in line_items if p["confidence"] is not None]
            line_avg_conf = round(sum(line_confs) / len(line_confs), 4) if line_confs else None
            if line_confs:
                all_confidences.extend(line_confs)
            lines.append(OCRLine(text=combined_line_text, confidence=line_avg_conf, page_number=page_number))

        page_text = "\n".join(line.text for line in lines)
        page_conf = round(sum(all_confidences) / len(all_confidences), 4) if all_confidences else None

        return OCRPage(
            page_number=page_number,
            text=page_text,
            confidence=page_conf,
            lines=lines,
        )

    def extract_text_from_file(self, file_path: Path) -> OCRResult:
        """Extract text from an image or scanned PDF file.

        Renders PDF pages to images if necessary, runs OCR, and normalizes
        into document text.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        ext = file_path.suffix.lower()

        if ext == ".pdf":
            return self._extract_from_pdf(file_path)
        elif ext in {".png", ".jpg", ".jpeg"}:
            image_bytes = file_path.read_bytes()
            page = self.extract_text_from_image(image_bytes, page_number=1)
            logger.info("Local OCR successfully processed image: %s", file_path.name)
            return OCRResult(
                text=page.text,
                extraction_method=self.provider_name,
                confidence=page.confidence,
                pages=[page],
            )
        else:
            raise ValueError(f"Unsupported file format for OCR: {ext}")

    def _extract_from_pdf(self, file_path: Path) -> OCRResult:
        """Render each page of a scanned PDF to an image and run OCR."""
        try:
            import pypdfium2 as pdfium
        except ImportError as e:
            raise OCREngineUnavailableError(
                "PDF page rendering unavailable — install pypdfium2: pip install pypdfium2"
            ) from e

        try:
            pdf = pdfium.PdfDocument(str(file_path))
        except Exception as e:
            raise OCREngineUnavailableError(f"Failed to open PDF document: {e}") from e

        pages: list[OCRPage] = []
        page_texts: list[str] = []
        page_confs: list[float] = []

        total_pages = len(pdf)
        for page_idx in range(total_pages):
            page_number = page_idx + 1
            try:
                page_obj = pdf[page_idx]
                pil_image = page_obj.render(scale=2).to_pil()
                buf = io.BytesIO()
                pil_image.save(buf, format="PNG")
                page_bytes = buf.getvalue()
                page_res = self.extract_text_from_image(page_bytes, page_number=page_number)
                pages.append(page_res)
                if page_res.text:
                    page_texts.append(f"[Page {page_number}]\n{page_res.text}")
                if page_res.confidence is not None:
                    page_confs.append(page_res.confidence)
            except Exception as e:
                logger.warning("Local OCR page rendering/extraction failed for page %d of %s: %e", page_number, file_path.name, e)
                pages.append(OCRPage(page_number=page_number, text="", confidence=None, lines=[]))

        combined_text = "\n\n".join(page_texts)
        doc_conf = round(sum(page_confs) / len(page_confs), 4) if page_confs else None

        logger.info("Local OCR successfully processed scanned PDF: %s (%d pages)", file_path.name, total_pages)
        return OCRResult(
            text=combined_text,
            extraction_method=self.provider_name,
            confidence=doc_conf,
            pages=pages,
        )
