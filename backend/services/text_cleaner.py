"""
Text Cleaner Service
Cleans and normalizes extracted text while preserving meaningful structure.
"""

import re
import logging

logger = logging.getLogger(__name__)


class TextCleaner:
    """Service for cleaning and normalizing extracted document text."""

    @staticmethod
    def clean(raw_text: str) -> str:
        """
        Clean and normalize raw extracted text.

        Operations:
        - Remove non-printable / control characters
        - Normalize unicode whitespace
        - Fix broken lines (re-join hyphenated line breaks)
        - Collapse excessive whitespace
        - Remove page markers artifacts
        - Preserve paragraph and section structure
        - Strip leading/trailing whitespace per line

        Args:
            raw_text: The raw extracted text.

        Returns:
            Cleaned and normalized text.
        """
        if not raw_text:
            return ""

        logger.info(f"Cleaning text ({len(raw_text)} chars)")
        text = raw_text

        # 1. Remove non-printable characters (keep newlines, tabs)
        text = re.sub(r"[^\S\n\t]+", " ", text)

        # 2. Remove common OCR / PDF artifacts
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # 3. Fix hyphenated line breaks (e.g., "termi-\nnation" -> "termination")
        text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

        # 4. Replace single newlines within a paragraph with spaces
        #    (preserve double newlines as paragraph separators)
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        # 5. Collapse multiple blank lines into double newline
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 6. Collapse multiple spaces into single space
        text = re.sub(r" {2,}", " ", text)

        # 7. Strip leading/trailing whitespace from each line
        lines = text.split("\n")
        lines = [line.strip() for line in lines]
        text = "\n".join(lines)

        # 8. Remove empty lines at start and end
        text = text.strip()

        # 9. Normalize common unicode characters
        replacements = {
            "\u2018": "'",  # Left single quote
            "\u2019": "'",  # Right single quote
            "\u201c": '"',  # Left double quote
            "\u201d": '"',  # Right double quote
            "\u2013": "-",  # En dash
            "\u2014": "--", # Em dash
            "\u2026": "...",  # Ellipsis
            "\u00a0": " ",  # Non-breaking space
            "\ufeff": "",   # BOM
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        logger.info(f"Text cleaned. Result: {len(text)} chars")
        return text
