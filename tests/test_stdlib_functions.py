import unittest
import json
from invariant import Policy, RuleSet

class TestStdlibFunctions(unittest.TestCase):
    def test_simple(self):
        policy = Policy.from_string(
        """
        from invariant import Message, PolicyViolation, match
        
        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            match(r".*X.*", msg.content)
        """)
        input = []
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(analysis_result.errors)

        input.append({"role": "assistant", "content": "Hello, Y"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(analysis_result.errors)

        input.append({"role": "assistant", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected one error, but got: " + str(analysis_result.errors)

if __name__ == "__main__":
    unittest.main()