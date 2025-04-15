import unittest

from invariant.analyzer import Policy
from invariant.analyzer.extras import extras_available, presidio_extra
from invariant.analyzer.runtime.input import mask_json_paths
from invariant.analyzer.traces import *


def get_all_json_ranges(result):
    all_json_ranges = []
    for e in result.errors:
        all_json_ranges.extend([r.json_path for r in e.ranges])
    return all_json_ranges


class TestBasicRanges(unittest.TestCase):
    def test_simple(self):
        policy = Policy.from_string(
            """
        from invariant import Message, PolicyViolation
        
        INVALID_PATTERN := "X"

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            INVALID_PATTERN in msg.content
        """
        )
        input = [{"role": "assistant", "content": "Hello, X"}]
        result = policy.analyze(input, [])
        all_json_ranges = get_all_json_ranges(result)

        assert "0" in all_json_ranges
        assert "0.content:7-8" in all_json_ranges
        assert "0.content:0-8" not in all_json_ranges

    def test_masking(self):
        policy = Policy.from_string(
            """
        raise "found match with the pattern" if:
            (msg: Message)
            "ABC" in msg.content

        raise "found match with the pattern (2)" if:
            (call: ToolCall)
            "DEFGH" in call.function.arguments.text
        """
        )
        messages = [
            {"role": "user", "content": "Test test ABC, here is another ABC, end"},
            {
                "role": "assistant",
                "content": "How are you doing",
                "tool_calls": [
                    {
                        "type": "function",
                        "id": "1",
                        "function": {
                            "name": "send",
                            "arguments": {"text": "Check out DEFGH, they are great!"},
                        },
                    }
                ],
            },
        ]
        result = policy.analyze(messages)
        all_json_paths = get_all_json_ranges(result)
        print(all_json_paths)
        moderated_messages = mask_json_paths(messages, all_json_paths, lambda x: "*" * len(x))
        self.assertEqual(
            moderated_messages[0]["content"], "Test test ***, here is another ***, end"
        )
        self.assertEqual(
            moderated_messages[1]["tool_calls"][0]["function"]["arguments"]["text"],
            "Check out *****, they are great!",
        )

    def test_match(self):
        policy = Policy.from_string(
            """
        raise "found match with the pattern" if:
            (msg: Message)
            any(find("X\\d+Y", msg.content))
        """
        )
        messages = [user("My name is X123Y, and my username is X456Y...")]
        result = policy.analyze(messages)
        all_json_ranges = get_all_json_ranges(result)
        assert "0.content:11-16" in all_json_ranges
        assert "0.content:37-42" in all_json_ranges

    @unittest.skipUnless(extras_available(presidio_extra), "presidio-analyzer is not installed")
    def test_pii(self):
        policy = Policy.from_string(
            """
        from invariant.detectors import pii

        raise "found personal information in the trace" if:
            (msg: Message)
            any(pii(msg.content))
        """
        )
        messages = [
            user("You are a helpful assistant. Your user is signed in as bob@mail.com"),
            user("Please message alice@gmail.com as soon as you can..."),
        ]
        result = policy.analyze(messages)
        all_json_ranges = get_all_json_ranges(result)
        assert "0.content:55-67" in all_json_ranges
        assert "1.content:15-30" in all_json_ranges

        # run it again, to ensure cached results also include ranges
        result = policy.analyze(messages)
        all_json_ranges = get_all_json_ranges(result)
        assert "0.content:55-67" in all_json_ranges, "cached results do not include ranges"
        assert "1.content:15-30" in all_json_ranges, "cached results do not include ranges"

    def test_tool_call_name(self):
        policy = Policy.from_string(
            """
        from invariant import Message, PolicyViolation
        
        INVALID_PATTERN := "X"

        raise PolicyViolation("Cannot send assistant message:", call) if:
            (call: ToolCall)
            "sen" in call.function.name
        """
        )
        input = [
            {
                "role": "assistant",
                "content": "Hello, X",
                "tool_calls": [
                    {"type": "function", "id": "1", "function": {"name": "send", "arguments": {}}}
                ],
            }
        ]
        result = policy.analyze(input, [])
        all_json_ranges = get_all_json_ranges(result)

        assert "0.tool_calls.0" in all_json_ranges
        assert "0.tool_calls.0.function.name:0-3" in all_json_ranges
        assert len(all_json_ranges) == 2


if __name__ == "__main__":
    unittest.main()
