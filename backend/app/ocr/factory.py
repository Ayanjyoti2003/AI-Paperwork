"""Paperwork Agent - OCR Provider Factory and Cache.

Resolves OCR provider according to OCR_PROVIDER environment variable:
- auto: Uses Textract if AWS credentials are configured; otherwise LocalOCRProvider.
- local: Always uses LocalOCRProvider.
- textract: Requires valid AWS credentials; raises OCRConfigurationError if missing.

Maintains an in-memory document OCR cache to avoid redundant processing.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from app.ocr.base import (
    OCRConfigurationError,
    OCRProvider,
    OCRResult,
)
from app.ocr.local import LocalOCRProvider
from app.ocr.textract import TextractOCRProvider, check_aws_credentials

logger = logging.getLogger(__name__)

# In-memory document OCR cache: (file_path_str, mtime, size_bytes) -> OCRResult
_OCR_CACHE: dict[tuple[str, float, int], OCRResult] = {}


def get_ocr_provider(provider_name: Optional[str] = None) -> OCRProvider:
    """Resolve and return the configured OCRProvider.

    Zero network requests are performed during resolution.
    """
    if provider_name is None:
        provider_name = os.environ.get("OCR_PROVIDER", "auto").strip().lower()

    if provider_name == "auto":
        if check_aws_credentials():
            logger.info("OCR provider resolved to Textract based on detected AWS credentials")
            return TextractOCRProvider()
        else:
            logger.info("OCR provider resolved to local OCR (offline mode)")
            return LocalOCRProvider()

    elif provider_name == "local":
        return LocalOCRProvider()

    elif provider_name == "textract":
        if not check_aws_credentials():
            raise OCRConfigurationError(
                "OCR_PROVIDER is set to 'textract' but no valid AWS credentials found in environment. "
                "Provide AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or standard AWS profile."
            )
        return TextractOCRProvider()

    else:
        raise OCRConfigurationError(
            f"Unsupported OCR_PROVIDER: '{provider_name}'. Supported values: auto, local, textract"
        )


def extract_document_ocr(
    file_path: Path,
    provider: Optional[OCRProvider] = None,
    use_cache: bool = True,
) -> OCRResult:
    """Extract text from an image or scanned document with in-memory caching.

    Args:
        file_path: Absolute or relative Path to target document.
        provider: Optional OCRProvider instance. If None, resolved via factory.
        use_cache: Whether to check and populate in-memory cache.

    Returns:
        OCRResult with normalized text, extraction method, and confidence.
    """
    resolved_path = file_path.resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Document file not found: {resolved_path}")

    stat = resolved_path.stat()
    cache_key = (str(resolved_path), stat.st_mtime, stat.st_size)

    if use_cache and cache_key in _OCR_CACHE:
        return _OCR_CACHE[cache_key]

    if provider is None:
        provider = get_ocr_provider()

    result = provider.extract_text_from_file(resolved_path)

    if use_cache:
        _OCR_CACHE[cache_key] = result

    return result


def clear_ocr_cache() -> None:
    """Clear all cached OCR results."""
    _OCR_CACHE.clear()
