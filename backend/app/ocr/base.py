"""Paperwork Agent - OCR Provider Base Abstraction and Data Models.

Defines the common interfaces, result dataclasses, and exceptions for
optical character recognition providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class OCRProviderError(Exception):
    """Base exception for OCR provider errors."""
    pass


class OCREngineUnavailableError(OCRProviderError):
    """Raised when an OCR engine dependency or local executable is missing."""
    pass


class OCRConfigurationError(OCRProviderError):
    """Raised when an OCR provider configuration is invalid or missing required credentials."""
    pass


@dataclass
class OCRLine:
    """A single recognized line of text with optional confidence score."""
    text: str
    confidence: Optional[float] = None
    page_number: int = 1


@dataclass
class OCRPage:
    """Text extracted from a single document page."""
    page_number: int
    text: str
    confidence: Optional[float] = None
    lines: list[OCRLine] = field(default_factory=list)


@dataclass
class OCRResult:
    """Complete extracted document text normalized across pages."""
    text: str
    extraction_method: str  # e.g., "local_ocr" or "textract"
    confidence: Optional[float] = None  # None if provider does not supply confidence
    pages: list[OCRPage] = field(default_factory=list)


class OCRProvider(ABC):
    """Abstract base class for OCR providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the OCR provider (e.g., 'local_ocr', 'textract')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider dependencies / configuration are available."""
        pass

    @abstractmethod
    def extract_text_from_image(self, image_bytes: bytes, page_number: int = 1) -> OCRPage:
        """Extract text from an image byte stream.

        Args:
            image_bytes: Raw bytes of the image (PNG, JPEG, etc.).
            page_number: Document page index (1-based).

        Returns:
            OCRPage containing normalized text, line details, and confidence.
        """
        pass

    @abstractmethod
    def extract_text_from_file(self, file_path: Path) -> OCRResult:
        """Extract text from an image or scanned document file.

        Args:
            file_path: Path to the target document.

        Returns:
            OCRResult containing combined normalized text across all pages.
        """
        pass
