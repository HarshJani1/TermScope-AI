"""
PDF Service
Extracts text from PDF files using PyPDFLoader.
"""

import logging
from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger(__name__)


class PDFService:
    """Service for extracting text from PDF files."""

    @staticmethod
    def extract_text(pdf_path: str) -> str:
        """
        Extract text from a PDF file using PyPDFLoader.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Extracted text as a single string (all pages concatenated).

        Raises:
            RuntimeError: If PDF extraction fails.
        """
        try:
            logger.info(f"Starting PDF extraction for: {pdf_path}")

            loader = PyPDFLoader(pdf_path)
            pages = loader.load()

            if not pages:
                raise RuntimeError(
                    "PDF appears to be empty or could not be parsed."
                )

            # Concatenate all pages with page markers
            text_parts = []
            for i, page in enumerate(pages, 1):
                page_text = page.page_content.strip()
                if page_text:
                    text_parts.append(f"--- Page {i} ---\n{page_text}")

            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                raise RuntimeError(
                    "PDF extraction returned empty text. "
                    "The PDF may contain only images — try uploading as an image for OCR."
                )

            logger.info(
                f"PDF extraction complete. Extracted {len(full_text)} characters "
                f"from {len(pages)} pages."
            )
            return full_text

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            raise RuntimeError(f"Failed to extract text from PDF: {str(e)}")
