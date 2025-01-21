"""Tests for the InvariantImage class."""

import base64
import os
from unittest.mock import patch

import pytest

from invariant.testing.custom_types.invariant_image import InvariantImage
from invariant.testing.custom_types.invariant_string import InvariantString
from invariant.testing.utils.packages import is_program_installed


@pytest.mark.parametrize(
    ("model", "client"),
    [
        ("gpt-4o", "OpenAI"),
        pytest.param(
            "claude-3-5-sonnet-20241022",
            "Anthropic",
            marks=pytest.mark.skipif(
                not os.getenv("ANTHROPIC_API_KEY"),
                reason="Skipping because ANTHROPIC_API_KEY is not set",
            ),
        ),
    ],
)
def test_vision_classifier(model, client):
    """Test the vision classifier."""
    with open(
        "invariant/testing/sample_tests/assets/Group_of_cats_resized.jpg", "rb"
    ) as image_file:
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


@pytest.mark.skipif(not is_program_installed("tesseract"), reason="Skip for now, needs tesseract")
def test_ocr_detector():
    """Test the OCR detector."""
    with open("invariant/testing/sample_tests/assets/inv_labs.png", "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    inv_img = InvariantImage(base64_image)
    assert inv_img.ocr_contains("agents")
    assert inv_img.ocr_contains("making", bbox={"x1": 50, "y1": 10, "x2": 120, "y2": 40})
    assert not inv_img.ocr_contains("LLM")

    assert inv_img.ocr_contains_all(["agents", "making"])
    assert not inv_img.ocr_contains_all(["agents", "making", "LLM"])
    assert inv_img.ocr_contains_any(["something", "agents", "abc"])
    assert not inv_img.ocr_contains_any(["something", "def", "abc"])


@pytest.fixture
def ocr_detector_mock():
    with patch(
        "invariant.custom_types.invariant_image.OCRDetector", autospec=True
    ) as mock_ocr_detector:
        mock_ocr_detector.return_value.contains.return_value = (
            True,
            [{"x1": 0, "x2": 10, "y1": 0, "y2": 10}],
        )
        yield mock_ocr_detector


# use the ocr_detector_mock fixture to test the ocr_contains method
def test_ocr_returns_bounding_boxes(ocr_detector_mock):
    """Test that the OCR detector returns bounding boxes."""
    with open("sample_tests/assets/inv_labs.png", "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    inv_img = InvariantImage(base64_image, addresses=["1"])
    res = inv_img.ocr_contains("agents")
    assert res.addresses
    assert "1:bbox-0,10,0,10" in res.addresses
    assert len(res.addresses) == 2

    # No bbox should be added when no address is present
    inv_img = InvariantImage(base64_image)
    res = inv_img.ocr_contains("agents")
    assert not res.addresses


def test_invariant_image_value_no_reassignment():
    """Test that the value of an InvariantImage cannot be reassigned."""
    with (
        open("invariant/testing/sample_tests/assets/inv_labs.png", "rb") as image_file_1,
        open(
            "invariant/testing//sample_tests/assets/Group_of_cats_resized.jpg", "rb"
        ) as image_file_2,
    ):
        base64_image_1 = base64.b64encode(image_file_1.read()).decode("utf-8")
        base64_image_2 = base64.b64encode(image_file_2.read()).decode("utf-8")
        inv_img = InvariantImage(base64_image_1)
        with pytest.raises(
            AttributeError, match="'value' attribute cannot be reassigned"
        ):
            inv_img.value = base64_image_2


@pytest.fixture
def ocr_detector_mock():
    with patch(
        "invariant.testing.custom_types.invariant_image.OCRDetector", autospec=True
    ) as mock_ocr_detector:
        mock_ocr_detector.return_value.contains.return_value = (
            True,
            [{"x1": 0, "x2": 10, "y1": 0, "y2": 10}],
        )
        yield mock_ocr_detector


def test_ocr_returns_bounding_boxes(ocr_detector_mock):
    """Test that the OCR detector returns bounding boxes."""
    with open("invariant/testing/sample_tests/assets/inv_labs.png", "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    inv_img = InvariantImage(base64_image, addresses=["1"])
    res = inv_img.ocr_contains("agents")
    assert res.addresses
    assert "1:bbox-0,10,0,10" in res.addresses
    assert len(res.addresses) == 2

    # No bbox should be added when no address is present
    inv_img = InvariantImage(base64_image)
    res = inv_img.ocr_contains("agents")
    assert not res.addresses
