"""Detect text in images using Tesseract OCR."""
import subprocess
import tempfile
from invariant.utils.packages import is_program_installed
from typing import Any, Dict, Optional
from PIL import Image

class OCRDetector:
    """Detect text in images using Tesseract OCR."""

    def __init__(self):
        """
        Initialize OCR detector with expected text to find in images
        """

    @classmethod
    def check_tesseract_installed(cls):
        """Check if Tesseract OCR is installed on the system."""
        try:
            subprocess.run(['tesseract', '--version'],
                           check=True, capture_output=True)
            return True
        except FileNotFoundError:
            return False

    def _is_in_bbox(self, bbox1: dict, bbox2: dict) -> bool:
        """Checks if bbox2 is inside bbox1"""
        return bbox1['x1'] <= bbox2['x1'] and bbox1['y1'] <= bbox2['y1'] and bbox1['x2'] >= bbox2['x2'] and bbox1['y2'] >= bbox2['y2']

    def contains(self, image: Image.Image, text: str, case_sensitive: bool = False, bbox: Optional[dict] = None) -> bool:
        """
        Detect if the expected text appears in the image using tesseract CLI

        Args:
            base64_image: Base64 encoded image string

        Returns:
            bool: True if expected text was found, False otherwise
        """
        if not is_program_installed("tesseract"):
            raise RuntimeError("Please install tesseract to use the contains function for images.")

        # Save image to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png') as temp_img:
            image.save(temp_img.name)

            # Run tesseract CLI command
            try:
                result = subprocess.run(
                    ['tesseract', temp_img.name, 'stdout',
                        '-c', 'tessedit_create_hocr=1'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.last_hocr = result.stdout  # disable=attribute-defined-outside-init
                extracted_text = self._extract_text_from_hocr(result.stdout)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Tesseract OCR failed: {e.stderr}") from e

        if not case_sensitive:
            text = text.lower()

        if bbox is not None:
            json_res = self.hocr_to_json(self.last_hocr)
            for word in json_res['words']:
                word_text = word['text']
                if not case_sensitive:
                    word_text = word_text.lower()
                if self._is_in_bbox(bbox, word['bbox']) and text in word_text:
                    return True
            return False

        if not case_sensitive:
            extracted_text = extracted_text.lower()
        return text in extracted_text

    def _extract_text_from_hocr(self, hocr: str) -> str:
        """Extract plain text from HOCR content."""
        from bs4 import \
            BeautifulSoup  # pylint: disable=import-outside-toplevel
        soup = BeautifulSoup(hocr, 'html.parser')
        return ' '.join(word.get_text() for word in soup.find_all(['span', 'div'], class_='ocrx_word'))

    def hocr_to_json(self, hocr: Optional[str] = None) -> Dict[str, Any]:
        """Convert HOCR content to JSON format.

        Args:
            hocr: HOCR content string. If None, uses last detection result

        Returns:
            Dict containing structured OCR data with word positions and confidence
        """
        from bs4 import \
            BeautifulSoup  # pylint: disable=import-outside-toplevel
        hocr_content = hocr or getattr(self, 'last_hocr', None)
        if not hocr_content:
            raise ValueError("No HOCR content available")

        soup = BeautifulSoup(hocr_content, 'html.parser')
        result = {
            'words': []
        }

        for word in soup.find_all(['span', 'div'], class_='ocrx_word'):
            bbox = word.get('title', '').split(';')[0].split(' ')[1:]
            if len(bbox) == 4:
                x1, y1, x2, y2 = map(int, bbox)
                result['words'].append({
                    'text': word.get_text(),
                    'bbox': {
                        'x1': x1,
                        'y1': y1,
                        'x2': x2,
                        'y2': y2
                    },
                    'confidence': float(word.get('title', '').split(';')[1].split(' ')[2])
                    if ';' in word.get('title', '') else None
                })

        return result
