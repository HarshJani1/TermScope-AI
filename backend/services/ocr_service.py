"""
OCR Service
Extracts text from image files using Tesseract OCR.
"""

import logging
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from images using Tesseract OCR."""

    @staticmethod
    def extract_text(image_path: str, tesseract_cmd: str = None) -> str:
        """
        Extract text from an image file using Tesseract OCR.

        Args:
            image_path: Path to the image file.
            tesseract_cmd: Optional path to the tesseract binary.

        Returns:
            Extracted text as a string.

        Raises:
            RuntimeError: If OCR extraction fails.
        """
        try:
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            logger.info(f"Starting OCR extraction for: {image_path}")

            image = Image.open(image_path)

            # Convert to RGB if necessary (handles RGBA, P, etc.)
            if image.mode not in ("L", "RGB"):
                image = image.convert("RGB")

            # Run OCR with English language
            text = pytesseract.image_to_string(image, lang="eng")

            if not text or not text.strip():
                logger.warning(f"OCR returned empty text for: {image_path}")
                raise RuntimeError(
                    "OCR could not extract any text from the image. "
                    "Please ensure the image contains readable text."
                )

            logger.info(
                f"OCR extraction complete. Extracted {len(text)} characters."
            )
            return text

        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract is not installed or not found in PATH")
            raise RuntimeError(
                "Tesseract OCR is not installed. Please install it: "
                "sudo apt-get install tesseract-ocr"
            )
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            raise RuntimeError(f"Failed to extract text from image: {str(e)}")
