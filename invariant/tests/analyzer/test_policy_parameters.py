import unittest

from invariant.analyzer import Monitor, Policy
from invariant.analyzer.runtime.runtime_errors import MissingPolicyParameter


class TestPolicyParameters(unittest.TestCase):
    def test_simple(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            input.pattern in msg.content
        """
        )
        input = [{"role": "assistant", "content": "Hello"}]
        analysis_result = policy.analyze(input, pattern="He")

        self.assertEqual(len(analysis_result.errors), 1)

    def test_parameter_missing(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            input.pattern in msg.content
        """
        )
        input = [{"role": "assistant", "content": "Hello"}]

        with self.assertRaises(MissingPolicyParameter):
            analysis_result = policy.analyze(input)

    def test_monitor_parameters(self):
        monitor = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation
        
        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            input.pattern in msg.content
        """,
            pattern="He",
        )
        input = [{"role": "assistant", "content": "Hello"}]
        errors = monitor.check([], input)

        self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
