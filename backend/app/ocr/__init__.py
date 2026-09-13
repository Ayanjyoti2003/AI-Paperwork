"""Paperwork Agent - Optical Character Recognition (OCR) Package.

Exposes OCR provider interfaces, exceptions, and factory methods.
"""

from app.ocr.base import (
    OCRConfigurationError,
    OCREngineUnavailableError,
    OCRLine,
    OCRPage,
    OCRProvider,
    OCRProviderError,
    OCRResult,
)
from app.ocr.factory import (
    clear_ocr_cache,
    extract_document_ocr,
    get_ocr_provider,
)
from app.ocr.local import LocalOCRProvider
from app.ocr.textract import TextractOCRProvider, check_aws_credentials

__all__ = [
    "OCRConfigurationError",
    "OCREngineUnavailableError",
    "OCRLine",
    "OCRPage",
    "OCRProvider",
    "OCRProviderError",
    "OCRResult",
    "LocalOCRProvider",
    "TextractOCRProvider",
    "check_aws_credentials",
    "clear_ocr_cache",
    "extract_document_ocr",
    "get_ocr_provider",
]
