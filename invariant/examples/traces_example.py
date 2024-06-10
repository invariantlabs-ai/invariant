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

    def __str__(self):
        return f"CallToSomething: {super().__str__()}"

def main():
    # define some policy
    policy = Policy.from_string(
    r"""
    # if the user asks about 'X', raise a violation exception
    raise PolicyViolation("Location data was passed to a get_temperature call", call=call) if:
        (call: ToolCall)
        call is tool:get_temperature({
            x: <LOCATION>
        })

    # check result after the operation
    raise PolicyViolation("get_temperature returned a value higher than 50", call=call) if:
        (call: ToolOutput)
        call.content > 50
    """)

    # simple chat messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the temperature in Paris, France?"},
        # assistant calls tool
        {
            "role": "assistant", 
            "content": None, 
            "tool_calls": [
                {
                    "id": "1",
                    "type": "function",
                    "function": {
                        "name": "get_temperature",
                        "arguments": {
                            "x": "Paris, France"
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