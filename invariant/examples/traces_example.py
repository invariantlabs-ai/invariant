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

@dataclass
class CallToSomething(Exception):
    call: ToolCall

def main():
    # define some policy
    policy = Policy.from_string(
    r"""
    from invariant import Message, match, PolicyViolation, ToolCall, ToolOutput
    from invariant.examples.traces_example import CallToSomething

    # if the user asks about 'X', raise a violation exception
    raise CallToSomething(call) if:
        (call: ToolCall)
        call.function.name == 'something'

    # check result after the operation
    raise PolicyViolation("result was too high", call) if:
        (call: ToolOutput)
        call.content > 2000
    """)

    # simple chat messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the result of something(2)?"},
        # assistant calls tool
        {
            "role": "assistant", 
            "content": None, 
            "tool_calls": [
                {
                    "id": "1",
                    "type": "function",
                    "function": {
                        "name": "something",
                        "arguments": {
                            "x": 2
                        }
                    }
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "1",
            "content": 2001
        }
    ]

    analysis_result = policy.analyze(messages)
    assert len(analysis_result.errors) == 2
    
    policy_violation = [e for e in analysis_result.errors if isinstance(e, PolicyViolation)][0]
    assert policy_violation.args[0] == "result was too high"
    assert policy_violation.args[1]["content"] == 2001

    something_call = [e for e in analysis_result.errors if type(e).__name__ == "CallToSomething"][0]
    assert something_call.call["function"]["name"] == "something"
    assert something_call.call["function"]["arguments"]["x"] == 2
    
    print(json.dumps(messages, indent=2))

# run 'main' as a test
class TestTraceAnalysisExample(unittest.TestCase):
    def test_trace_analysis_example(self):
        main()

if __name__ == "__main__":
    unittest.main()