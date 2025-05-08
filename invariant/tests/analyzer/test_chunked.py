import unittest

from invariant.analyzer import Monitor, Policy
from invariant.analyzer.traces import chunked


class TestChunked(unittest.TestCase):
    def test_simple(self):
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

        pending_input = [chunked({"role": "assistant", "content": "Hello, X"})]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 1, "Expected one error, but got: " + str(errors)
        assert "Cannot send assistant message" in str(errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: "
            + str(errors[0])
        )

        pending_input = [chunked({"role": "assistant", "content": "Hello, Y"})]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 0, "Expected no errors, but got: " + str(errors)

    def test_simple_but_multiple_text_chunks(self):
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
                    {"type": "text", "text": "Hello, "},
                    {"type": "text", "text": "X"},
                ],
            }
        ]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 1, "Expected one error, but got: " + str(errors)
        assert "Cannot send assistant message" in str(errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: "
            + str(errors[0])
        )

        pending_input = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hello, "},
                    {"type": "text", "text": "Y"},
                ],
            }
        ]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 0, "Expected no errors, but got: " + str(errors)

    def test_contains_in_text_chunk(self):
        # tests that 'abc' in message.content works both when 'abc' is in chunk 0 or chunk 1
        policy = Policy.from_string(
            """

raise "pattern found" if:
    (msg: Message)
    msg.role == "assistant"
    "abc" in msg.content
"""
        )

        # in second chunk
        input = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hello, "},
                    {"type": "text", "text": "aa abc aa"},
                ],
            }
        ]

        result = policy.analyze(input, [])
        assert len(result.errors) == 1, "Expected one error, but got: " + str(result)

        # in no chunk
        input = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hello, "},
                    {"type": "text", "text": "adc"},
                ],
            }
        ]

        result = policy.analyze(input, [])
        assert len(result.errors) == 0, "Expected no errors, but got: " + str(result)

        # in first chunk
        input = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "aa abc aa"},
                    {"type": "text", "text": "Hello, "},
                ],
            }
        ]
        result = policy.analyze(input, [])
        assert len(result.errors) == 1, "Expected one error, but got: " + str(result)
