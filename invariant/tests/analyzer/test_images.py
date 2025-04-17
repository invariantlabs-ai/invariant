import base64
import io
import os
import unittest

from PIL import Image

from invariant.analyzer import Monitor
from invariant.analyzer.traces import image
from invariant.tests.analyzer.utils import is_program_installed, is_remote_run

file_name = "image_with_text_b64.txt"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name), "r") as f:
    letter_a_image = f.read()


# generate a green square 100x100px image in base64
def generate_green_square():
    # Create a 100x100px green square
    image = Image.new("RGB", (100, 100), (0, 255, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"


class TestImages(unittest.TestCase):
    def test_images(self):
        """
        Simply check that images can be created as messages
        """
        monitor = Monitor.from_string(
            """
            from invariant import Message, PolicyViolation
            
            INVALID_PATTERN := "X"

            raise PolicyViolation("Cannot send assistant message:", msg) if:
                (msg: Message)
                msg.role == "assistant"
                (chunk: str) in text(msg.content)
                INVALID_PATTERN in chunk
            """
        )

        input = []
        monitor.check(input, [])

        pending_input = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello, world! X",
                    },
                ],
            },
            image(generate_green_square()),
        ]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 1, "Expected 1 error, but got: " + str(len(errors))
        assert "Cannot send assistant message" in str(errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: "
            + str(errors[0])
        )

    def test_images_in_multipart_messages(self):
        """
        Simply check that images can be part of multipart messages.
        """
        monitor = Monitor.from_string(
            """
            from invariant import Message, PolicyViolation
            
            INVALID_PATTERN := "X"

            raise PolicyViolation("Cannot send assistant message:", msg) if:
                (msg: Message)
                msg.role == "assistant"
                (chunk: str) in text(msg.content)
                INVALID_PATTERN in chunk
            """
        )

        input = []
        monitor.check(input, [])

        pending_input = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello, world! X",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": generate_green_square(),
                        },
                    },
                ],
            },
        ]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 1, "Expected 1 error, but got: " + str(len(errors))
        assert "Cannot send assistant message" in str(errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: "
            + str(errors[0])
        )

    @unittest.skipUnless(
        is_program_installed("tesseract") and not is_remote_run(), "tesseract is not installed"
    )
    def test_ocr(self):
        """
        Simply check that OCR can be performed on images.
        """

        monitor = Monitor.from_string(
            """
            from invariant.parsers.ocr import ocr

            raise PolicyViolation("found bad vibes!", msg) if:
                (msg: Message)
                image_data := image(msg)
                ocr_result := ocr(image_data)[0]
                'it was the worst of times' in ocr_result
            """
        )

        input = []
        monitor.check(input, [])

        pending_input = [
            image(f"data:image/png;base64,{letter_a_image}"),
        ]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 1, "Expected 1 error, but got: " + str(len(errors))
        assert "found bad vibes" in str(errors[0]), (
            "Expected to find 'found pii' in error message, but got: " + str(errors[0])
        )
