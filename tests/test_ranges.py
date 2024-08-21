from invariant import Policy
import unittest
import json
from invariant import Policy, RuleSet, Monitor

class TestBasicRanges(unittest.TestCase):
    def test_simple(self):
        policy = Policy.from_string(
        """
        from invariant import Message, PolicyViolation, match
        
        INVALID_PATTERN := "X"

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            INVALID_PATTERN in msg.content
        """)
        input = [{
            "role": "assistant",
            "content": "Hello, X"
        }]
        result = policy.analyze(input, [])

        all_json_ranges = []
        for e in result.errors:
            all_json_ranges.extend([r.json_path for r in e.ranges])

        assert "0" in all_json_ranges
        assert "0.content:7-8" in all_json_ranges
        assert "0.content:0-8" not in all_json_ranges

    def test_tool_call_name(self):
        policy = Policy.from_string(
        """
        from invariant import Message, PolicyViolation, match
        
        INVALID_PATTERN := "X"

        raise PolicyViolation("Cannot send assistant message:", call) if:
            (call: ToolCall)
            "sen" in call.function.name
        """)
        input = [{
            "role": "assistant",
            "content": "Hello, X",
            "tool_calls": [
                {
                    "type": "function",
                    "id": "1",
                    "function": {
                        "name": "send",
                        "arguments": {}
                    }
                }
            ]
        }]
        result = policy.analyze(input, [])

        all_json_ranges = []
        for e in result.errors:
            all_json_ranges.extend([r.json_path for r in e.ranges])

        assert "0.tool_calls.0" in all_json_ranges
        assert "0.tool_calls.0.function.name:0-3" in all_json_ranges
        assert len(all_json_ranges) == 2

if __name__ == "__main__":
    unittest.main()