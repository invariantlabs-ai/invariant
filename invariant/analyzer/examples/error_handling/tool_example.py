"""
Demonstrates how to integrate the Invariant Agent Analyzer with a custom
tool calling framework, including support for custom error handlers.
"""

import json
import unittest
from dataclasses import dataclass

from invariant.analyzer import Monitor
from invariant.analyzer.monitor import stack, wrappers
from invariant.analyzer.stdlib.invariant import ToolCall
from invariant.analyzer.stdlib.invariant.errors import PolicyViolation


@dataclass
class SomethingCall(Exception):
    call: ToolCall


def main():
    def is_tool_call(msg):
        # assistant, content is None and tool_calls is not empty
        return msg["role"] == "assistant" and msg["content"] is None and len(msg["tool_calls"]) > 0

    def tool(chat: list[dict], monitor: Monitor):
        def decorator(func):
            name = func.__name__

            def wrapped(tool_input, *args, **kwargs):
                if not isinstance(tool_input, dict):
                    raise ValueError(
                        f"Expected a dictionary of all tool parameters, but got: {tool_input} (note that @tool functions must be called with a dictionary of arguments and do not support positional arguments)"
                    )
                # remove tool call from chat
                tool_call_msg = chat.pop(-1)
                assert is_tool_call(tool_call_msg), f"Expected a tool call message: {tool_call_msg}"
                assert len(tool_call_msg["tool_calls"]) == 1, (
                    f"Expected a single tool call: {tool_call_msg}"
                )
                tool_call = tool_call_msg["tool_calls"][0]
                assert tool_call["function"]["name"] == name, (
                    f"Expected a tool call to {name} as last message, but got: {tool_call}"
                )

                # analysis current state + this tool call
                analysis_result = monitor.analyze(chat + [tool_call_msg])
                if len(analysis_result.errors) > 0:
                    raise analysis_result.errors[0]

                # apply the handlers (make sure side-effects apply to tool_call_msg)
                analysis_result.execute_handlers()

                # determine wrappers
                def actual_tool(tool_input, **kwargs):
                    # update the tool call arguments, based on actual arguments
                    tool_call_msg["tool_calls"][0]["function"]["arguments"].update(kwargs)
                    # call the actual function
                    return func(**tool_input)

                wrapped_tool = stack(wrappers(analysis_result) + [actual_tool])
                result = wrapped_tool(tool_call_msg["tool_calls"][0]["function"]["arguments"])

                # add the tool call back to the chat
                chat.append(tool_call_msg)
                chat.append(
                    {
                        "role": "assistant",
                        "content": result,
                        "tool_call_id": tool_call_msg["tool_calls"][0]["id"],
                    }
                )

                # finally, apply policy again (for ToolOutput analysis)
                analysis_result = monitor.analyze(chat)
                if len(analysis_result.errors) > 0:
                    raise analysis_result.errors[0]

                # apply the handlers (make sure  side-effects apply to tool output)
                analysis_result.execute_handlers()

                return result

            return wrapped

        return decorator

    # define some policy
    monitor = Monitor.from_string(
        r"""
    from invariant import Message, match, PolicyViolation, ToolCall, ToolOutput
    from invariant.analyzer.examples.tool_example import SomethingCall

    # if the user asks about 'X', raise a violation exception
    raise SomethingCall(call) if:
        (call: ToolCall)
        call.function.name == 'something'

    # check result after the operation
    raise PolicyViolation("result was too high", call) if:
        (call: ToolOutput)
        call.content > 2000
    """
    )

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
                    "function": {"name": "something", "arguments": {"x": 2}},
                }
            ],
        },
    ]

    @tool(chat=messages, monitor=monitor)
    def something(x):
        return x + 1

    @monitor.on(SomethingCall)
    def update_inputs_to_10(error: SomethingCall):
        call = error.call
        call["function"]["arguments"]["x"] = 1000

    @monitor.on(SomethingCall)
    def wrap_tool(
        tool_input: dict, error: SomethingCall = None, call_next: callable = None, **kwargs
    ):
        result = call_next(tool_input)
        return result * 2

    @monitor.on(PolicyViolation)
    def handle_too_high_output(error: PolicyViolation):
        call = error.args[1]
        call["content"] = 1

    something({"x": 2})

    print(json.dumps(messages, indent=2))

    assert messages[-1]["content"] == 1
    assert messages[-2]["tool_calls"][0]["function"]["arguments"]["x"] == 1000


# run 'main' as a test
class TestToolWrappingIntegration(unittest.TestCase):
    def test_tool_call_integration(self):
        main()


if __name__ == "__main__":
    unittest.main()
