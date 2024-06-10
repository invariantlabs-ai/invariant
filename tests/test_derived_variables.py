import unittest
import json
from invariant import Policy, RuleSet

class TestDerivedVariables(unittest.TestCase):
    def test_subselect(self):
        policy = Policy.from_string(
        """
        raise "error" if:
            (msg: Message)
            (line: str) in msg.content
            "a" in line
        """)

        # no match
        input = [{
            "role": "assistant",
            "content": [
                "Hello, X",
                "Hello, Y"
            ]
        }]
        errors = policy.analyze(input).errors
        assert len(errors) == 0

        # one match
        input = [{
            "role": "assistant",
            "content": [
                "Hello, X",
                "Hello, Y",
                "Hello, a"
            ]
        }]
        errors = policy.analyze(input).errors
        assert len(errors) == 1
    
    def test_twolevel_subselect(self):
        policy = Policy.from_string(
        """
        raise "error" if:
            (msg: Message)
            (line: list) in msg.content
            (word: str) in line
            "a" == word
        """)

        # no match
        input = [{
            "role": "assistant",
            "content": [
                ["Hello", "X"],
                ["Hello", "Y"]
            ]
        }]
        errors = policy.analyze(input).errors
        assert len(errors) == 0

        # one match
        input = [{
            "role": "assistant",
            "content": [
                ["Hello", "X"],
                ["Hello", "Y"],
                ["Hello", "a"]
            ]
        }]
        errors = policy.analyze(input).errors
        assert len(errors) == 1

        # two matches
        input = [{
            "role": "assistant",
            "content": [
                ["Hello", "X"],
                ["Hello", "Y"],
                ["Hello", "a"],
                ["Hello", "a"]
            ]
        }]
        errors = policy.analyze(input).errors
        assert len(errors) == 2

    def test_exclude_submodels(self):
        policy = Policy.from_string(
        """
        raise PolicyViolation(line=line, word=word) if:
            (msg: Message)
            msg.a > 2 # cond 1
            (line: list) in msg.content
            (word: str) in line
            # cond 2
            len(line) < 4 
            # cond 3
            "a" == word
        """)

        # no match
        input = [
            {
                "role": "assistant",
                "content": [
                    ["msg 1", "X"],
                    ["msg 1", "Y"]
                ],
                "a": 1 # excluded by the first condition
            },
            {
                "role": "assistant",
                "content": [
                    ["msg 2", "X"],
                    ["msg 2", "Y"],
                    ["msg 2", "a"]
                ],
                "a": 3 # included by the first condition
            },
            {
                "role": "assistant",
                "content": [
                    ["msg 3", "X"],
                    ["msg 3", "Y"],
                    ["msg 3", "a"],
                    ["msg 3", "a"] # excluded by the second condition
                ],
                "a": 3 # included by the first condition
            }
        ]
        errors = policy.analyze(input).errors
        assert len(errors) == 1

if __name__ == "__main__":
    unittest.main()