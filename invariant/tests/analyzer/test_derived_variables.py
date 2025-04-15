import unittest

from invariant.analyzer import Policy
from invariant.analyzer.policy import analyze_trace
from invariant.analyzer.traces import *


class TestDerivedVariables(unittest.TestCase):
    def test_subselect(self):
        policy = Policy.from_string(
            """
        raise "error" if:
            (msg: Message)
            (line: str) in msg.content.splitlines()
            "a" in line
        """
        )

        # no match
        input = [{"role": "assistant", "content": "Hello, X\nHello, Y"}]
        errors = policy.analyze(input).errors
        assert len(errors) == 0

        # one match
        input = [{"role": "assistant", "content": "Hello, X\nHello, Y\nHello, a"}]
        errors = policy.analyze(input).errors
        assert len(errors) == 1

    def test_twolevel_subselect(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation(line=line, word=word) if:
            (msg: Message)
            (line: str) in msg.content.splitlines()
            (word: str) in line.split(" ")
            "a" == word
        """
        )
        # no match
        input = [{"role": "assistant", "content": "Hello, X\nHello, Y"}]
        errors = policy.analyze(input).errors
        assert len(errors) == 0

        # two matches
        input = [{"role": "assistant", "content": "Hello, X\nHello, Y\nHello, a\nHello, a"}]
        errors = policy.analyze(input).errors
        assert len(errors) == 2

    def test_exclude_submodels(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation(line=line, word=word) if:
            (msg: Message)
            msg.metadata["a"] > 2 # cond 1
            lines := msg.content.splitlines()
            (line: str) in lines
            (word: str) in line.split(",")
            # cond 2
            len(lines) < 4
            # cond 3
            "a" == word
        """
        )

        # no match
        input = [
            {
                "role": "assistant",
                "content": "msg 1,X\nmsg 1,Y",
                "metadata": {
                    "a": 1,
                },
            },
            {
                "role": "assistant",
                "content": "msg 2,X\nmsg 2,Y\nmsg 2,a",
                "metadata": {
                    "a": 3,
                },
            },
            {
                "role": "assistant",
                "content": "msg 3,X\nmsg 3,Y\nmsg 3,a\nmsg 3,a",
                "metadata": {
                    "a": 3,
                },
            },
        ]
        errors = policy.analyze(input).errors
        assert len(errors) == 1

    def test_predicate_derived(self):
        policy_str_template = """
        from invariant.detectors import python_code

        raise PolicyViolation("found same imports") if:
            (out1: ToolOutput)
            (out2: ToolOutput)
            out1 -> out2
            (import1: str) in python_code(out1).imports
            (import2: str) in python_code(out2).imports
            import1 == import2
        """
        trace = [
            tool("1", "import os\nimport sys\nimport numpy as np\nfrom sklearn import svm\n"),
            tool("2", "import abc\nimport shlex\n"),
        ]
        self.assertEqual(len(analyze_trace(policy_str_template, trace).errors), 0)
        trace[1]["content"] = "import abc\nimport os\n"
        self.assertEqual(len(analyze_trace(policy_str_template, trace).errors), 1)

    def test_multiple(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation(line=line, word=word) if:
            (msg: Message)
            (line: str) in msg.content.splitlines()
            (word: str) in line.split(" ")
            "a" == word
        """
        )
        input = [
            {"role": "user", "content": "Hello, X\nHello, a"},
            {"role": "assistant", "content": "Bye Y"},
            {"role": "assistant", "content": "Bye a\nBye b"},
        ]
        res = policy.analyze(input)
        self.assertEqual(len(res.errors), 2)


if __name__ == "__main__":
    unittest.main()
