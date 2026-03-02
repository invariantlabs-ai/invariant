import unittest

from sonomos_firewall.analyzer import Monitor, Policy
from sonomos_firewall.analyzer.stdlib.invariant.errors import UnhandledError
from sonomos_firewall.analyzer.traces import chunked


class TestConstants(unittest.TestCase):
    def test_simple(self):
        monitor = Monitor.from_string(
            """
        from sonomos_firewall import Message, PolicyViolation
        
        INVALID_PATTERN := "X"

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            INVALID_PATTERN in msg.content
        """
        )
        input = []
        monitor.check(input, [])

        pending_input = [{"role": "assistant", "content": "Hello, X"}]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 1, "Expected one error, but got: " + str(errors)
        assert "Cannot send assistant message" in str(errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: "
            + str(errors[0])
        )

        pending_input = [{"role": "assistant", "content": "Hello, Y"}]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 0, "Expected no errors, but got: " + str(errors)

    def test_simple_chunked(self):
        monitor = Monitor.from_string(
            """
        from sonomos_firewall import Message, PolicyViolation

        INVALID_PATTERN := "X"

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            INVALID_PATTERN in msg.content
        """
        )
        input = []
        monitor.check(input, [])

        pending_input = [chunked({"role": "assistant", "content": "Hello X"})]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 1, "Expected one error, but got: " + str(errors)
        assert "Cannot send assistant message" in str(errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: "
            + str(errors[0])
        )

        pending_input = [{"role": "assistant", "content": "Hello, Y"}]
        errors = monitor.check(input, pending_input)
        input.extend(pending_input)

        assert len(errors) == 0, "Expected no errors, but got: " + str(errors)

    def test_ref(self):
        policy = Policy.from_string(
            """
        from sonomos_firewall import Message, PolicyViolation

        INVALID_PATTERN1 := "X"
        INVALID_PATTERN2 := "Y"
        INVALID_PATTERN := INVALID_PATTERN1 + INVALID_PATTERN2

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            INVALID_PATTERN in msg.content
        """
        )

        input = [{"role": "assistant", "content": "Hello, XY"}]
        with self.assertRaises(UnhandledError) as context:
            analysis_result = policy.analyze(input, raise_unhandled=True)


if __name__ == "__main__":
    unittest.main()
