""" Tests for the InvariantImage class. """

import base64

import pytest
from invariant.custom_types.invariant_image import InvariantImage
from invariant.custom_types.invariant_string import InvariantString
from invariant.utils.packages import is_program_installed


@pytest.mark.parametrize(
    ("model", "client"),
    [
        ("gpt-4o", "OpenAI"),
        pytest.param(
            "claude-3-5-sonnet-20241022",
            "Anthropic",
            marks=pytest.mark.skip(
                "Skipping because we have not setup the API key in the CI"
            ),
        ),
    ],
)
def test_vision_classifier(model, client):
    """Test the vision classifier."""
    with open("sample_tests/assets/Group_of_cats_resized.jpg", "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    img = InvariantImage(base64_image)
    res = img.llm_vision(
        "What is in the image?",
        ["cats", "dogs", "birds", "none"],
        model=model,
        client=client,
    )
    assert isinstance(res, InvariantString) and res.value == "cats"
    res = img.llm_vision(
        "How many cats are in the image?",
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        model=model,
        client=client,
    )
    assert isinstance(res, InvariantString) and res.value == "3"


@pytest.mark.skipif(
    not is_program_installed("tesseract"), reason="Skip for now, needs tesseract"
)
def test_ocr_detector():
    """Test the OCR detector."""
    with open("sample_tests/assets/inv_labs.png", "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    inv_img = InvariantImage(base64_image)
    assert inv_img.ocr_contains("agents")
    assert inv_img.ocr_contains(
        "making", bbox={"x1": 50, "y1": 10, "x2": 120, "y2": 40}
    )
    assert not inv_img.ocr_contains("LLM")
