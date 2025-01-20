"""A custom type for an invariant image."""

import base64
import io
import logging
from typing import Optional

from invariant.testing.scorers.llm.classifier import Classifier
from invariant.testing.scorers.utils.ocr import OCRDetector
from PIL import Image

from .invariant_bool import InvariantBool
from .invariant_string import InvariantString

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class InvariantImage(InvariantString):
    """An invariant image."""

    def __init__(self, value: str, addresses: Optional[list[str]] = None):
        if value.startswith("local_base64_img: "):
            value = value[16:]
        super().__init__(value, addresses)
        image_data = base64.b64decode(value)
        self.image = Image.open(io.BytesIO(image_data))
        # Set the image type. For example:
        # JPEG format becomes "image/jpeg" MIME type.
        self.image_type = f"image/{self.image.format.lower()}"
        assert isinstance(self.image, Image.Image)

    def llm_vision(
        self,
        prompt: str,
        options: list[str],
        model: str = "gpt-4o",
        client: str = "OpenAI",
        use_cached_result: bool = True,
    ) -> InvariantString:
        """Check if the value is similar to the given string using an LLM.

        Args:
            prompt (str): The prompt to use for the LLM.
            options (list[str]): The options to use for the LLM.
            model (str): The model to use for the LLM.
            client (invariant.scorers.llm.clients.client.SupportedClients): The client to use for the LLM.
            use_cached_result (bool): Whether to use a cached result if available.

        Returns:
            InvariantString: The result of the LLM classification

        """
        llm_clf = Classifier(
            prompt=prompt,
            options=options,
            model=model,
            client=client,
            vision=True,
        )
        res = llm_clf.classify_vision(
            self.value, image_type=self.image_type, use_cached_result=use_cached_result
        )
        return InvariantString(res, self.addresses)

    def ocr_contains(
        self,
        text: str | InvariantString,
        case_sensitive: bool = False,
        bbox: Optional[dict] = None,
    ) -> InvariantBool:
        """Check if the value contains the given text using OCR.

        Args:
            text (str | InvariantString): The text to search for within the image.
            case_sensitive (bool, optional): Whether the text search should be case-sensitive. Defaults to False.
            bbox (Optional[dict], optional): A bounding box to limit the search area within the image.
                                             The dictionary should contain keys 'x1', 'x2', 'y1', and 'y2'. Defaults to None.

        Returns:
            InvariantBool: True if the text is found in the image, False otherwise.

        """
        addresses = self.addresses
        if isinstance(text, InvariantString):
            addresses.extend(text.addresses)
            text = text.value

        res, bboxes = OCRDetector().contains(self.image, text, case_sensitive, bbox)

        # This assumes that the first address (if any) contains the message index!
        if addresses and bboxes:
            try:
                message_index = addresses[0].split(":")[0]

                # Add the bounding box coordinates to the addresses.
                for bbox_coords in bboxes:
                    x1, y1, x2, y2 = bbox_coords.values()
                    addresses.append(f"{message_index}:bbox-{x1},{y1},{x2},{y2}")

            except IndexError:
                logger.warning(
                    "Failed to extract message index for bounding box construction"
                )

        return InvariantBool(res, addresses)

    def ocr_contains_any(
        self,
        texts: list[str | InvariantString],
        case_sensitive: bool = False,
        bbox: Optional[dict] = None,
    ) -> InvariantBool:
        """Check if the value contains any of the given pieces of text in `texts` using OCR.

        Args:
            texts (list[str | InvariantString]): The texts to search for within the image.
            case_sensitive (bool, optional): Whether the text search should be case-sensitive. Defaults to False.
            bbox (Optional[dict], optional): A bounding box to limit the search area within the image.
                                             The dictionary should contain keys 'x1', 'x2', 'y1', and 'y2'. Defaults to None.

        Returns:
            InvariantBool: True if any of the texts are found in the image, False otherwise.

        """
        for text in texts:
            if res := self.ocr_contains(text, case_sensitive, bbox):
                return res

        return InvariantBool(False, self.addresses)

    def ocr_contains_all(
        self,
        texts: list[str | InvariantString],
        case_sensitive: bool = False,
        bbox: Optional[dict] = None,
    ) -> InvariantBool:
        """Check if the value contains all of the given pieces of text in `texts` using OCR.

        Args:
            texts (list[str | InvariantString]): The texts to search for within the image.
            case_sensitive (bool, optional): Whether the text search should be case-sensitive. Defaults to False.
            bbox (Optional[dict], optional): A bounding box to limit the search area within the image.
                                             The dictionary should contain keys 'x1', 'x2', 'y1', and 'y2'. Defaults to None.

        Returns:
            InvariantBool: True if all of the texts are found in the image, False otherwise.

        """
        for text in texts:
            if not (res := self.ocr_contains(text, case_sensitive, bbox)):
                return res
        return InvariantBool(True, self.addresses)
