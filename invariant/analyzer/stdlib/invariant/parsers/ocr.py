from invariant.analyzer.runtime.functions import cached
from invariant.analyzer.runtime.nodes import Image as ImageNode
from invariant.analyzer.stdlib.invariant.builtins import image

OCR_ANALYZER = None


@cached
async def _ocr_detect(image_data: str | list[ImageNode | str] | ImageNode) -> str:
    """
    Detects text and returns the text and bounding boxes of the detected text.
    """
    global OCR_ANALYZER
    if OCR_ANALYZER is None:
        from invariant.analyzer.runtime.utils.ocr import OCRAnalyzer

        OCR_ANALYZER = OCRAnalyzer()

    return OCR_ANALYZER.detect_all(image_data)


async def ocr(image_data: str | list[ImageNode | str] | ImageNode) -> list[str]:
    """
    Extracts text from an image.

    Args:
        image_data: base64 encoded image or list of base64 encoded images

    Returns:
        str: The extracted text.
    """
    ocr_results: list[str] = []
    for image_node in image(image_data):
        ocr_result = await _ocr_detect(image_node)
        ocr_results.append(ocr_result)
    return ocr_results
