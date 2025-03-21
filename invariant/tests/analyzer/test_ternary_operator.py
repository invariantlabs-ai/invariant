import unittest
from invariant.analyzer.language.parser import parse
from invariant.analyzer.policy import Policy, PolicyLoadingError, analyze_trace


class TestTernaryOperator(unittest.TestCase):
    def test_ternary_operator_parsing(self):
        """Test that a policy with a ternary operator can be parsed correctly."""
        policy = parse("""
            from invariant import Message

            raise "Contains example phrase" if:
                (message: Message)
                True if ("example1" in message.content) else ("example2" in message.content)
            """, verbose=True)

        # Verify the policy parsed successfully
        self.assertEqual(len(policy.errors), 0, f"Parse errors found: {policy.errors}")

        # Test that we can create a Policy from this
        try:
            policy_obj = Policy(policy)
            self.assertIsNotNone(policy_obj)
        except PolicyLoadingError as e:
            self.fail(f"Failed to load policy with ternary operator: {e}")

    def test_ternary_operator_evaluation(self):
        """Test that a policy with a ternary operator evaluates correctly."""
        policy_str = """
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Contains example phrase") if:
            (message: Message)
            message.role == "assistant"
            True if ("example1" in message.content) else ("example2" in message.content)
        """

        # Should trigger with example1
        trace_with_example1 = [
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "Hello, here's example1 for you."}
        ]
        result1 = analyze_trace(policy_str, trace_with_example1)
        self.assertEqual(len(result1.errors), 1, "Policy should have triggered for example1")

        # Should trigger with example2
        trace_with_example2 = [
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "Hello, here's example2 for you."}
        ]
        result2 = analyze_trace(policy_str, trace_with_example2)
        self.assertEqual(len(result2.errors), 1, "Policy should have triggered for example2")

        # Should not trigger without either example
        trace_without_examples = [
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "Hello, how can I help you?"}
        ]
        result3 = analyze_trace(policy_str, trace_without_examples)
        self.assertEqual(len(result3.errors), 0, "Policy should not have triggered without examples")
