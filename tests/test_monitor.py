import unittest
import json
from invariant import Policy, Monitor

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

if __name__ == "__main__":
    unittest.main()