import copy
import unittest

from invariant.analyzer import Monitor
from invariant.analyzer.stdlib.invariant import *


class TestMonitor(unittest.TestCase):
    def test_simple(self):
        policy = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation
        
        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
        """
        )
        input = []

        input.append({"role": "user", "content": "Hello, world!"})
        analysis_result = policy.analyze(input)

        input.append({"role": "assistant", "content": "Hello, user 1"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) > 0, "Expected at least one error, but got: " + str(
            analysis_result.errors
        )
        error = analysis_result.errors[0]
        assert "user 1" in str(error), (
            "Expected to find 'user 1' in error message, but got: " + str(e)
        )

        input.append({"role": "assistant", "content": "Hello, user 2"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected only one extra error, but got: " + str(
            analysis_result.errors
        )
        error = analysis_result.errors[0]
        assert "user 2" in str(error), (
            "Expected to find 'user 2' in error message, but got: " + str(error)
        )

        input.append({"role": "user", "content": "Hello, world!"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )
        # no error raised, since it is not an assistant message

    def test_append_action(self):
        policy = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "user"
        """
        )

        input = []

        input.append({"role": "user", "content": "Hello, world!"})
        analysis_result = policy.analyze(input)
        assert input[0]["content"] == "Hello, world!", (
            "Expected 'Hello, world!' after first append, but got: " + input[0]["content"]
        )

        input.append({"role": "user", "content": "Hello, world!"})
        assert input[0]["content"] == "Hello, world!", (
            "Expected 'Hello, world!' after second append, but got: " + input[0]["content"]
        )
        assert input[1]["content"] == "Hello, world!", (
            "Expected 'Hello, world!' after second append, but got: " + input[1]["content"]
        )

        input.append({"role": "assistant", "content": "Hello, world"})
        assert input[0]["content"] == "Hello, world!", (
            "Expected 'Hello, world!' after append, but got: " + input[0]["content"]
        )
        assert input[1]["content"] == "Hello, world!", (
            "Expected 'Hello, world!' after append, but got: " + input[1]["content"]
        )
        assert input[2]["content"] == "Hello, world", (
            "Expected 'Hello, world' after append, but got: " + input[2]["content"]
        )

    def test_objects(self):
        monitor = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Cannot send user message:", msg) if:
            (msg: Message)
            msg.role == "user"
        """
        )

        events = [
            {"role": "user", "content": "Hello, world!"},
            {"role": "assistant", "content": "Hello, world!"},
        ]
        input = []
        input += [events[0]]
        res = monitor.analyze(input)
        self.assertTrue(len(res.errors) == 1)
        self.assertIsInstance(res.errors[0], ErrorInformation)

        input += [events[1]]
        res = monitor.analyze(input)
        self.assertTrue(len(res.errors) == 0)

        res = monitor.analyze(copy.deepcopy(input))
        self.assertTrue(len(res.errors) == 0)

    def test_analyze_pending(self):
        policy = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Cannot send user message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            "A" in msg.content
        """
        )

        past_events = [
            Message(role="user", content="Hello, world!"),
            Message(role="assistant", content="Hello AB!"),
            Message(role="assistant", content="Hello AXYZ!"),
        ]
        pending_events = [
            Message(role="assistant", content="Hello A!"),
            Message(role="assistant", content="Hello BC!"),
            Message(role="assistant", content="Bye A!"),
        ]

        res = policy.analyze_pending(
            [e.model_dump() for e in past_events],
            [e.model_dump() for e in pending_events],
        )

        self.assertEqual(len(res.errors), 2)
        self.assertIsInstance(res.errors[0], ErrorInformation)
        self.assertTrue("Hello A!" in str(res.errors[0]))
        self.assertTrue("Bye A!" in str(res.errors[1]))

    def test_analyze_pending_detects_tool_calls(self):
        """Make sure that tool calls can raise when using analyze_pending"""

        error_message = "dummy_tool should not be called"

        policy = Monitor.from_string(f"""
        raise PolicyViolation("{error_message}") if:
            (call: ToolCall)
            call is tool:dummy_tool
        """)

        messages = [
            {
                "role": "user",
                "content": "whatever",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_5",
                        "type": "function",
                        "function": {"name": "dummy_tool", "arguments": {"name": "123"}},
                    }
                ],
            },
        ]

        res = policy.analyze_pending(messages[:-1], [messages[-1]])

        self.assertEqual(len(res.errors), 1)
        self.assertIsInstance(res.errors[0], ErrorInformation)
        self.assertTrue(error_message in str(res.errors[0]))


if __name__ == "__main__":
    unittest.main()
