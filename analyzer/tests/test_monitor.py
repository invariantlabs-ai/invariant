import copy
import unittest
import json
from invariant import Policy, Monitor
from invariant.stdlib.invariant import *

class TestMonitor(unittest.TestCase):
    def test_simple(self):
        policy = Monitor.from_string(
        """
        from invariant import Message, PolicyViolation
        
        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
        """)
        input = []

        input.append({"role": "user", "content": "Hello, world!"})
        analysis_result = policy.analyze(input)

        input.append({"role": "assistant", "content": "Hello, user 1"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) > 0, "Expected at least one error, but got: " + str(analysis_result.errors)
        error = analysis_result.errors[0]
        assert "user 1" in str(error), "Expected to find 'user 1' in error message, but got: " + str(e)
        
        input.append({"role": "assistant", "content": "Hello, user 2"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected only one extra error, but got: " + str(analysis_result.errors)
        error = analysis_result.errors[0]
        assert "user 2" in str(error), "Expected to find 'user 2' in error message, but got: " + str(e)
        
        input.append({"role": "user", "content": "Hello, world!"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(analysis_result.errors)
        # no error raised, since it is not an assistant message

    def test_append_action(self):
        policy = Monitor.from_string(
        """
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "user"
        """)

        input = []

        @policy.on("PolicyViolation")
        def handle_user_msg(msg):
            msg["content"] += "!"

        input.append({"role": "user", "content": "Hello, world!"})
        analysis_result = policy.analyze(input)
        assert input[0]["content"] == "Hello, world!", "Expected 'Hello, world!' after first append, but got: " + input[0]["content"]

        input.append({"role": "user", "content": "Hello, world!"})
        assert input[0]["content"] == "Hello, world!", "Expected 'Hello, world!' after second append, but got: " + input[0]["content"]
        assert input[1]["content"] == "Hello, world!", "Expected 'Hello, world!' after second append, but got: " + input[1]["content"]

        input.append({"role": "assistant", "content": "Hello, world"})
        assert input[0]["content"] == "Hello, world!", "Expected 'Hello, world!' after append, but got: " + input[0]["content"]
        assert input[1]["content"] == "Hello, world!", "Expected 'Hello, world!' after append, but got: " + input[1]["content"]
        assert input[2]["content"] == "Hello, world", "Expected 'Hello, world' after append, but got: " + input[2]["content"]

    def test_objects(self):
        policy = Monitor.from_string(
        """
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Cannot send user message:", msg) if:
            (msg: Message)
            msg.role == "user"
        """)

        events = [
            Message(role="user", content="Hello, world!"),
            Message(role="assistant", content="Hello, world!")
        ]
        input = []
        input += [events[0]]
        res = policy.analyze(input)
        self.assertTrue(len(res.errors) == 1)
        self.assertIsInstance(res.errors[0], ErrorInformation)

        input += [events[1]]
        res = policy.analyze(input)
        self.assertTrue(len(res.errors) == 0)

        import copy
        res = policy.analyze(copy.deepcopy(input))
        self.assertTrue(len(res.errors) == 0)

    def test_analyze_pending(self):
        policy = Monitor.from_string(
        """
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Cannot send user message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            "A" in msg.content
        """)

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

        res = policy.analyze_pending(past_events, pending_events)

        self.assertEqual(len(res.errors), 2)
        self.assertIsInstance(res.errors[0], ErrorInformation)
        self.assertTrue("Hello A!" in str(res.errors[0]))
        self.assertTrue("Bye A!" in str(res.errors[1]))

if __name__ == "__main__":
    unittest.main()