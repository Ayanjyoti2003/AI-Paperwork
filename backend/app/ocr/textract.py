"""Paperwork Agent - AWS Textract OCR Provider.

Extracts text using AWS Textract (detect_document_text) with line-level ordering
and confidence tracking. Strictly preserves privacy: zero logging of document
contents, raw responses, credentials, or PII.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Optional

from app.ocr.base import (
    OCRConfigurationError,
    OCREngineUnavailableError,
    OCRLine,
    OCRPage,
    OCRProvider,
    OCRProviderError,
    OCRResult,
)

logger = logging.getLogger(__name__)


def check_aws_credentials() -> bool:
    """Check whether AWS credentials are configured without making network calls."""
    import os

    # Check common AWS environment variables
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return True

    # Check boto3 session credentials
    try:
        import boto3
        session = boto3.Session()
        creds = session.get_credentials()
        return creds is not None and creds.access_key is not None
    except Exception:
        return False


class TextractOCRProvider(OCRProvider):
    """AWS Textract optical character recognition provider."""

    def __init__(self, client: Any = None) -> None:
        self._client = client

    @property
    def provider_name(self) -> str:
        return "textract"

    def is_available(self) -> bool:
        """Check if boto3 is installed and credentials exist."""
        try:
            import boto3  # noqa: F401
            return check_aws_credentials()
        except ImportError:
            return False

    def _get_client(self) -> Any:
        """Lazily initialize boto3 textract client."""
        if self._client is None:
            try:
                import boto3
            except ImportError as e:
                raise OCRConfigurationError(
                    "AWS SDK (boto3) is not installed. Install it via: pip install boto3"
                ) from e

            if not check_aws_credentials():
                raise OCRConfigurationError(
                    "AWS Textract requested but no valid AWS credentials found in environment. "
                    "Configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or standard AWS profile."
                )

            try:
                self._client = boto3.client("textract")
            except Exception as e:
                raise OCRConfigurationError(
                    f"Failed to initialize AWS Textract client: {e}"
                ) from e

        return self._client

    def extract_text_from_image(self, image_bytes: bytes, page_number: int = 1) -> OCRPage:
        """Call AWS Textract detect_document_text on image bytes."""
        client = self._get_client()

        try:
            response = client.detect_document_text(Document={"Bytes": image_bytes})
        except Exception as e:
            logger.error("AWS Textract detect_document_text API call failed (page %d)", page_number)
            raise OCRProviderError(
                f"AWS Textract text detection failed: {e}. Check AWS credentials, region, and IAM permissions."
            ) from e

        lines: list[OCRLine] = []
        confidences: list[float] = []

        blocks = response.get("Blocks", [])
        for block in blocks:
            if block.get("BlockType") == "LINE":
                text_str = block.get("Text", "").strip()
                raw_conf = block.get("Confidence")
                conf = None
                if raw_conf is not None:
                    try:
                        # AWS Textract confidence is 0.0 to 100.0; normalize to 0.0 to 1.0
                        conf = round(float(raw_conf) / 100.0, 4)
                        confidences.append(conf)
                    except (ValueError, TypeError):
                        pass

                if text_str:
                    lines.append(OCRLine(text=text_str, confidence=conf, page_number=page_number))

        page_text = "\n".join(line.text for line in lines)
        page_conf = round(sum(confidences) / len(confidences), 4) if confidences else None

        logger.info("Textract detected %d lines of text (page %d)", len(lines), page_number)
        return OCRPage(
            page_number=page_number,
            text=page_text,
            confidence=page_conf,
            lines=lines,
        )

    def extract_text_from_file(self, file_path: Path) -> OCRResult:
        """Extract text from a file using Textract."""
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        ext = file_path.suffix.lower()

        if ext == ".pdf":
            return self._extract_from_pdf(file_path)
        elif ext in {".png", ".jpg", ".jpeg"}:
            image_bytes = file_path.read_bytes()
            page = self.extract_text_from_image(image_bytes, page_number=1)
            logger.info("Textract successfully processed image: %s", file_path.name)
            return OCRResult(
                text=page.text,
                extraction_method=self.provider_name,
                confidence=page.confidence,
                pages=[page],
            )
        else:
            raise ValueError(f"Unsupported file format for Textract OCR: {ext}")

    def _extract_from_pdf(self, file_path: Path) -> OCRResult:
        """Render scanned PDF pages to images and call Textract on each."""
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
            except OCRProviderError:
                raise
            except Exception as e:
                logger.warning("Textract PDF page extraction failed for page %d of %s: %s", page_number, file_path.name, e)
                pages.append(OCRPage(page_number=page_number, text="", confidence=None, lines=[]))

        combined_text = "\n\n".join(page_texts)
        doc_conf = round(sum(page_confs) / len(page_confs), 4) if page_confs else None

        logger.info("Textract successfully processed scanned PDF: %s (%d pages)", file_path.name, total_pages)
        return OCRResult(
            text=combined_text,
            extraction_method=self.provider_name,
            confidence=doc_conf,
            pages=pages,
        )
