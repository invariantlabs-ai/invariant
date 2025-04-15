import base64
import io
from enum import Enum

import pytesseract
from PIL import Image, UnidentifiedImageError

from invariant.analyzer.runtime.nodes import Image as ImageNode
from invariant.analyzer.runtime.utils.base import BaseDetector


class ImageFormat(str, Enum):
    """Supported image formats."""

    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"


def get_image_data_from_node(node: ImageNode) -> str:
    """
    Extract image data from an ImageNode.

    Args:
        node: The ImageNode containing image URL information.

    Returns:
        The image URL string or an empty string if not found.
    """
    image_url = node.image_url
    if isinstance(image_url, dict):
        return image_url.get("url", "")
    return ""


def extract_image_format(image_data: str, _expception_print_limit: int = 100) -> ImageFormat:
    """Extract the image format from the image data."""
    if not isinstance(image_data, str):
        raise ValueError(f"Invalid image data: {image_data}")

    for image_type in ImageFormat:
        if image_data.startswith(f"data:image/{image_type.value};base64,"):
            return image_type.value
    raise ValueError(f"Unsupported image data: {image_data[:_expception_print_limit]}...")


def extract_image_data(image_data: str) -> str:
    """Extract the image data from the image data."""
    image_format = extract_image_format(image_data)
    return image_data[len(f"data:image/{image_format};base64,") :]


def process_image_data(image_data: str) -> str:
    """Process a single image and extract the text.

    Args:
        image_data: The image data to process.

    Returns:
        OCRResult: The detected text.
    """
    try:
        image_data = extract_image_data(image_data)
        image = Image.open(io.BytesIO(base64.b64decode(image_data)))

        extracted_text = pytesseract.image_to_string(image).strip()
        text_lines = [line for line in extracted_text.split("\n") if line.strip()]

        return " ".join(text_lines)
    except base64.binascii.Error as e:
        raise ValueError(f"Invalid base64 encoding: {e}") from e
    except UnidentifiedImageError as e:
        raise ValueError(f"Could not identify image format: {e}") from e


class OCRAnalyzer(BaseDetector):
    def detect_all(self, image_data: str):
        """
        Given a single image, extract the text.

        Args:
            image_data: The image data to process.

        Returns:
            The detected text.
        """
        return process_image_data(image_data)

    async def adetect(self, image_data: str):
        return self.detect_all(image_data)
