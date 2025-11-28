import pytesseract
from PIL import Image
import logging
import os

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self, languages='eng'):
        self.languages = languages

    def extract_text(self, image_path):
        """
        Extracts text from an image file using Tesseract.
        Returns a list of strings (lines).
        """
        try:
            # Open image with Pillow
            img = Image.open(image_path)
            
            # Extract text
            text = pytesseract.image_to_string(img, lang=self.languages)
            
            # Split into lines and filter empty ones
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return lines
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return []

# Singleton instance
ocr_service = OCRService()
