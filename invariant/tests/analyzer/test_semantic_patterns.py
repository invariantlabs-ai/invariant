import unittest
import json
from invariant.analyzer import Policy, RuleSet
from invariant.analyzer.extras import extras_available, presidio_extra, transformers_extra

def pattern_matches(semantic_pattern, arguments, tool_name="something"):
    policy = Policy.from_string(
    f"""
    from invariant import ToolCall

    raise "found match" if:
        (call: ToolCall)
        call is {semantic_pattern}
    """)
    
    input = [{
        "role": "assistant", 
        "content": None, 
        "tool_calls": [
            {
                "id": "1",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
        ] 
    }]
    result = policy.analyze(input)
    return len(result.errors) == 1

class TestConstants(unittest.TestCase):
    def test_simple(self):
        assert pattern_matches("tool:something", {
            "x": 2
        })

        assert pattern_matches("""tool:something({
            x: 2
        })""", {
            "x": 2
        })

        assert not pattern_matches("tool:something", {
            "x": 3
        }, tool_name="another")

        assert not pattern_matches("""tool:something({
            x: 3
        })""", {
            "x": 2
        })

    def test_regex(self):
        assert pattern_matches("tool:something({x: \"\\d+\"})", {
            "x": "2"
        })

        assert not pattern_matches("tool:something({x: \"\\d+\"})", {
            "x": "a"
        })

        # dates
        assert pattern_matches("tool:something({x: \"\\d{4}-\\d{2}-\\d{2}\"})", {
            "x": "2021-01-01"
        })

        # negative test
        assert not pattern_matches("tool:something({x: \"\\d{4}-\\d{2}-\\d{2}\"})", {
            "x": "2021-01-01T00:00:00"
        })

    @unittest.skipUnless(extras_available(presidio_extra, transformers_extra), "At least one of presidio-analyzer, transformers, and torch are not installed")
    def test_value_type(self):
        assert pattern_matches("tool:something({to: <EMAIL_ADDRESS>})", {
            "to": "bob@mail.com"
        })

        assert not pattern_matches("tool:something({to: <EMAIL_ADDRESS>})", {
            "to": "hello"
        })

        assert pattern_matches("tool:something({content: <LOCATION>})", {
            "content": "I am writing you from Zurich, Switzerland"
        })

        assert not pattern_matches("tool:something({content: <LOCATION>})", {
            "content": "I am writing you from my home"
        })

        assert pattern_matches("tool:something({phone: <MODERATED>, name: \"A.*\"})", {
            "phone": "I hate this shit.",
            "name": "Alice"
        })

    @unittest.skipUnless(extras_available(presidio_extra, transformers_extra), "At least one of presidio-analyzer, transformers, and torch are not installed")
    def test_nested_args(self):
        assert pattern_matches("""tool:something({args: [
            "A.*",
            <EMAIL_ADDRESS>,
            {
                "content": <MODERATED>
            }
        ]})""", {
            "args": [
                "Alice",
                "alice@mail.com",
                {
                    "content": "I hate this shit."
                }
            ]
        })

    def test_wildcard(self):
        assert pattern_matches("""tool:something({args: [
            "A.*",
            *,
            "C.*"
        ]})""", {
            "args": [
                "Alice",
                "Bob",
                "Clement"
            ]
        })

        assert not pattern_matches("""tool:something({args: [
            "A.*",
            "D.*",
            "C.*"
        ]})""", {
            "args": [
                "Alice",
                "Bob",
                "Clement"
            ]
        })

if __name__ == "__main__":
    unittest.main()