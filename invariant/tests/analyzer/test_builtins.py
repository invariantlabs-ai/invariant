import unittest

from invariant.analyzer import Policy
from invariant.analyzer.traces import assistant, tool, tool_call, user


class TestBuiltins(unittest.TestCase):
    def test_tool_call_name(self):
        policy = Policy.from_string("""
        raise "error" if:
            (tool_output: ToolOutput)
            tool_call(tool_output).function.name == "some_tool"
        """)

        trace = [
            user("What is the result of something?"),
            assistant(None, tool_call("1", "some_tool", {})),
            tool("1", "some_output"),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) == 1

    def test_tool_call_name_no_match(self):
        policy = Policy.from_string("""
        raise "error" if:
            (tool_output: ToolOutput)
            tool_call(tool_output).function.name == "some_tool"
        """)

        trace = [
            user("What is the result of something?"),
            assistant(None, tool_call("1", "some_other_tool", {})),
            tool("1", "some_output"),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) == 0
