import unittest
from invariant.analyzer import ast
from invariant.analyzer.language.ast import PolicyError
from invariant.analyzer import Policy, RuleSet, Monitor
from invariant.analyzer.traces import user, assistant, tool_call, tool, system

class TestQuantifiers(unittest.TestCase):
    def test_quantifier_with_args(self):
        policy = Policy.from_string("""
from invariant import count

raise "found result" if:
    count(min=2, max=4):
        (tc: ToolCall)
        tc is tool:get_inbox
    """)
        trace = [
            # injection in alt text
            assistant("1", tool_call("1", "get_inbox", {})),
            tool("1", "tool output"),
            assistant("1", tool_call("2", "get_inbox", {})),
            tool("2", "tool output"),
        ]

        errors = policy.analyze(trace).errors
        self.assertEqual(len(errors), 1)

    def test_quantifier_with_args_notrigger(self):
        policy = Policy.from_string("""
from invariant import count

raise "found result" if:
    count(min=2, max=4):
        (tc: ToolCall)
        tc is tool:get_inbox
    """)
        trace = [
            # injection in alt text
            assistant("1", tool_call("1", "get_inbox", {})),
            tool("1", "tool output"),
        ]

        errors = policy.analyze(trace).errors
        self.assertEqual(len(errors), 0)

    def test_quantifier_with_args_notrigger(self):
        policy = Policy.from_string("""
from invariant import count

raise "found result" if:
    not count(min=2, max=4):
        (tc: ToolCall)
        tc is tool:get_inbox
    """)
        trace = [
            # injection in alt text
            assistant("1", tool_call("1", "get_inbox", {})),
            tool("1", "tool output"),
        ]

        errors = policy.analyze(trace).errors
        self.assertEqual(len(errors), 1)

    def test_quantifier_without_args(self):
        policy = Policy.from_string("""
from invariant import forall

raise "found result" if:
    forall:
        (tc: ToolCall)
        tc is tool:get_inbox
    """)
        trace = [
            # injection in alt text
            assistant("1", tool_call("1", "get_inbox", {})),
            tool("1", "tool output"),
        ]

        errors = policy.analyze(trace).errors
        self.assertEqual(len(errors), 1)

    def test_quantifier_without_args_notrigger(self):
        policy = Policy.from_string("""
from invariant import forall

raise "found result" if:
    forall:
        (tc: ToolCall)
        tc is tool:get_inbox
    """)
        trace = [
            # injection in alt text
            assistant("1", tool_call("1", "get_inbox", {})),
            tool("1", "tool output"),
            assistant("1", tool_call("2", "send_mail", {})),
            tool("2", "tool output"),
        ]

        errors = policy.analyze(trace).errors
        self.assertEqual(len(errors), 0)

    def test_negated_quantifier_without_args_notrigger(self):
        policy = Policy.from_string("""
from invariant import forall

raise "found result" if:
    not forall:
        (tc: ToolCall)
        tc is tool:get_inbox
    """)
        trace = [
            # injection in alt text
            assistant("1", tool_call("1", "get_inbox", {})),
            tool("1", "tool output"),
            assistant("1", tool_call("2", "send_mail", {})),
            tool("2", "tool output"),
        ]

        errors = policy.analyze(trace).errors
        self.assertEqual(len(errors), 1)

    def test_quantifier_closure(self):
        policy = Policy.from_string("""
from invariant import count, forall

raise "found result" if:
    (call: ToolCall)
    call is tool:scroll_down

    count(min=5):
        (output: ToolOutput)
        call -> output
        "django" in output.content
    """)
        
        trace = [
            assistant("1", tool_call("1", "scroll_down", {})),
            tool("1", "django"),
            tool("1", "django"),
            tool("1", "django"),
            tool("1", "django"),
            tool("1", "django"),
            tool("1", "django"),
        ]

        errors = policy.analyze(trace).errors
        self.assertEqual(len(errors), 1)

    def test_quantifier_closure_neg(self):
        policy = Policy.from_string("""
from invariant import count, forall

raise "found result" if:
    (call: ToolCall)
    call is tool:scroll_down

    count(min=5):
        (output: ToolOutput)
        call -> output
        "django" in output.content
    """)
        
        trace = [
            assistant("1", tool_call("1", "scroll_down", {})),
            tool("1", "django"),
            tool("1", "django"),
            tool("1", "django"),
            tool("1", "django")
        ]

        errors = policy.analyze(trace).errors
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()