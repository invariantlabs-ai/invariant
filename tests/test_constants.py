import unittest
import json
from invariant import Policy, RuleSet, Monitor

class TestConstants(unittest.TestCase):
    def test_simple(self):
        monitor = Monitor.from_string(
        """
        from invariant import Message, PolicyViolation, match
        
        INVALID_PATTERN := "X"

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            INVALID_PATTERN in msg.content
        """)
        input = []
        monitor.check(input)

        input.append({"role": "assistant", "content": "Hello, X"})
        analysis_result = monitor.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected one error, but got: " + str(analysis_result.errors)
        assert "Cannot send assistant message" in str(analysis_result.errors[0]), "Expected to find 'Cannot send assistant message' in error message, but got: " + str(e)

        input.append({"role": "assistant", "content": "Hello, Y"})
        analysis_result = monitor.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(analysis_result.errors)

    def test_ref(self):
        policy = Policy.from_string(
        """
        from invariant import Message, PolicyViolation, match

        INVALID_PATTERN1 := "X"
        INVALID_PATTERN2 := "Y"
        INVALID_PATTERN := INVALID_PATTERN1 + INVALID_PATTERN2

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            INVALID_PATTERN in msg.content
        """)

        input = [{
            "role": "assistant",
            "content": "Hello, XY"
        }]
        with self.assertRaises(Exception) as context:
            analysis_result = policy.analyze(input, raise_unhandled=True)


if __name__ == "__main__":
    unittest.main()