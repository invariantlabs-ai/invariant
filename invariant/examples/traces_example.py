"""
Demonstrates how to apply the ISA to a pre-recorded agent trace
to detect potential policy violations.
"""

import json
from invariant import parse, Policy, Input, ValidatedOperation

from invariant.stdlib.invariant.errors import UpdateMessage, UpdateMessageHandler, PolicyViolation
from invariant.stdlib.invariant import ToolCall
from dataclasses import dataclass
import unittest
from invariant import Input

@dataclass
class CallToSomething(Exception):
    call: ToolCall

    def __str__(self):
        return f"CallToSomething: {super().__str__()}"

def main():
    # define some policy
    policy = Policy.from_string(
    r"""
    # if the user asks about 'X', raise a violation exception
    raise PolicyViolation("Do not leak the user's email address", call=call) if:
        (call: ToolCall)
        call is tool:search_web({
            q: <EMAIL_ADDRESS>
        })

    # check result after the operation
    raise PolicyViolation("The response should not contain 'France'", call=result) if:
        (result: ToolOutput)
        result is tool:search_web
        "France" in result.content
    """)

    # simple chat messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Your user is signed in as bob@mail.com"},
        {"role": "user", "content": "Please do some reasearch on Paris."},
        # assistant calls 'search_web' tool
        {"role": "assistant", "content": None, "tool_calls": [ { "id": "1", "type": "function",
            "function": { "name": "search_web", "arguments": { "q": "bob@mail.com want's to know about Paris" }}}]},
        {"role": "tool", "tool_call_id": "1", "content": "Paris is the capital of France."}
    ]

    print(json.dumps(messages, indent=2))
    
    analysis_result = policy.analyze(messages)
    print(analysis_result)
    assert len(analysis_result.errors) == 2
    

# run 'main' as a test
class TestTraceAnalysisExample(unittest.TestCase):
    def test_trace_analysis_example(self):
        main()

if __name__ == "__main__":
    unittest.main()