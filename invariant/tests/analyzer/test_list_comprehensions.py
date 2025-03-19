import unittest
from invariant.analyzer import parse, Policy, PolicyLoadingError
from invariant.analyzer.policy import analyze_trace


class TestListComprehension(unittest.TestCase):
    def test_list_comprehension_parsing(self):
        """Test that a policy with a list comprehension can be parsed correctly."""
        policy = parse("""
        raise "Contains banned phrase" if:
            (message: Message)
            any([phrase in message.content for phrase in ["example1", "example2", "example3"]])
        """)

        # Verify the policy parsed successfully
        self.assertEqual(len(policy.errors), 0, f"Parse errors found: {policy.errors}")

        # Test that we can create a Policy from this
        try:
            policy_obj = Policy(policy)
            self.assertIsNotNone(policy_obj)
        except PolicyLoadingError as e:
            self.fail(f"Failed to load policy with list comprehension: {e}")

    def test_list_comprehension_evaluation(self):
        """Test that a policy with a list comprehension evaluates correctly."""
        policy_str = """
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Contains banned phrase") if:
            (message: Message)
            message.role == "assistant"
            any([phrase in message.content for phrase in ["example1", "example2", "example3"]])
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

        # Should not trigger without any examples
        trace_without_examples = [
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "Hello, how can I help you?"}
        ]
        result3 = analyze_trace(policy_str, trace_without_examples)
        self.assertEqual(len(result3.errors), 0, "Policy should not have triggered without examples")

    def test_list_comprehension_with_condition(self):
        """Test that list comprehensions can include conditional filtering."""
        policy_str = """
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Contains filtered words") if:
            (message: Message)
            message.role == "assistant"
            any([word in message.content for word in ["apple", "banana", "cherry", "date", "elderberry"] if len(word) > 5])
        """

        # Should trigger with "banana" (length > 5)
        trace1 = [
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "I like banana smoothies."}
        ]
        result1 = analyze_trace(policy_str, trace1)
        self.assertEqual(len(result1.errors), 1, "Policy should have triggered for banana")

        # Should not trigger with "apple" (length <= 5)
        trace2 = [
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "I like apple pie."}
        ]
        result2 = analyze_trace(policy_str, trace2)
        self.assertEqual(len(result2.errors), 0, "Policy should not have triggered for apple")