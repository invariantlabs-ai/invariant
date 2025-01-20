"""Detect text in images using Tesseract OCR."""

import subprocess
import tempfile
from typing import Any, Dict, Optional

from invariant.testing.utils.packages import is_program_installed
from PIL import Image


class OCRDetector:
    """Detect text in images using Tesseract OCR."""

    def __init__(self):
        """Initialize OCR detector with expected text to find in images."""

    @classmethod
    def check_tesseract_installed(cls):
        """Check if Tesseract OCR is installed on the system."""
        try:
            subprocess.run(["tesseract", "--version"], check=True, capture_output=True)
            return True
        except FileNotFoundError:
            return False

    def _is_in_bbox(self, bbox1: dict, bbox2: dict) -> bool:
        """Check if bbox2 is inside bbox1."""
        return (
            bbox1["x1"] <= bbox2["x1"]
            and bbox1["y1"] <= bbox2["y1"]
            and bbox1["x2"] >= bbox2["x2"]
            and bbox1["y2"] >= bbox2["y2"]
        )

    def contains(
        self,
        image: Image.Image,
        text: str,
        case_sensitive: bool = False,
        bbox: Optional[dict] = None,
    ) -> tuple[bool, list[dict[str, int]]]:
        """Detect if the expected text appears in the image using Tesseract OCR.

        Args:
            image (Image.Image): The image in which to search for the text.
            text (str): The text to search for within the image.
            case_sensitive (bool, optional): Whether the text search should be case-sensitive. Defaults to False.
            bbox (Optional[dict], optional): A bounding box to limit the search area within the image.
                                             The dictionary should contain keys 'x1', 'x2', 'y1', and 'y2'. Defaults to None.

        Retruns:
            bool: True if the text is found in the image, False otherwise.
            list: List of bounding box coordinates (scaled by image size) of the text in the image.

        """
        image_width, image_height = image.size
        if not is_program_installed("tesseract"):
            raise RuntimeError(
                "Please install tesseract to use the contains function for images."
            )

        # Save image to temporary file
        with tempfile.NamedTemporaryFile(suffix=".png") as temp_img:
            image.save(temp_img.name)

            # Run tesseract CLI command
            try:
                result = subprocess.run(
                    [
                        "tesseract",
                        temp_img.name,
                        "stdout",
                        "-c",
                        "tessedit_create_hocr=1",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.last_hocr = result.stdout  # disable=attribute-defined-outside-init

            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Tesseract OCR failed: {e.stderr}") from e

        # Extract text from HOCR content
        json_res = self.hocr_to_json(self.last_hocr)

        found = False
        bounding_boxes = []

        # Iterate over words in the OCR result
        for word in json_res["words"]:
            word_text = word["text"]

            # If case_sensitive is False, convert both text and word to lowercase
            if not case_sensitive:
                word_text = word_text.lower()
                text = text.lower()

            # If the text is not in the word, skip
            if not (text in word_text):
                continue

            # If bbox is set and the word is not in the bbox, skip
            if bbox and not self._is_in_bbox(bbox, word["bbox"]):
                continue

            # Otherwise, add the bounding box to the list
            found = True
            bounding_boxes.append(
                self._scale_bbox(word["bbox"], image_width, image_height)
            )

        return found, bounding_boxes

    def _scale_bbox(self, bbox: dict, image_width: int, image_height: int) -> dict:
        """Scale bounding box to be relative to image size."""
        return {
            "x1": float(bbox["x1"] / image_width),
            "y1": float(bbox["y1"] / image_height),
            "x2": float(bbox["x2"] / image_width),
            "y2": float(bbox["y2"] / image_height),
        }

    def _extract_text_from_hocr(self, hocr: str) -> str:
        """Extract plain text from HOCR content."""
        from bs4 import BeautifulSoup  # pylint: disable=import-outside-toplevel

        soup = BeautifulSoup(hocr, "html.parser")
        return " ".join(
            word.get_text()
            for word in soup.find_all(["span", "div"], class_="ocrx_word")
        )

    def hocr_to_json(self, hocr: Optional[str] = None) -> Dict[str, Any]:
        """Convert HOCR content to JSON format.

        Args:
            hocr: HOCR content string. If None, uses last detection result

        Returns:
            Dict containing structured OCR data with word positions and confidence

        """
        from bs4 import BeautifulSoup  # pylint: disable=import-outside-toplevel

        hocr_content = hocr or getattr(self, "last_hocr", None)
        if not hocr_content:
            raise ValueError("No HOCR content available")

        soup = BeautifulSoup(hocr_content, "html.parser")
        result = {"words": []}

        for word in soup.find_all(["span", "div"], class_="ocrx_word"):
            bbox = word.get("title", "").split(";")[0].split(" ")[1:]
            if len(bbox) == 4:
                x1, y1, x2, y2 = map(int, bbox)
                result["words"].append(
                    {
                        "text": word.get_text(),
                        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                        "confidence": (
                            float(word.get("title", "").split(";")[1].split(" ")[2])
                            if ";" in word.get("title", "")
                            else None
                        ),
                    }
                )

        return result
