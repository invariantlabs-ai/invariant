"""
Demonstrates how to use the Invariant Analyzer for real-time monitoring
of an OpenAI-based function-calling agents.

Execution of this script is aborted by the monitor if a security violation is detected.

Snippet adapted from OpenAI's example code at https://platform.openai.com/docs/guides/function-calling.
"""

import json
import unittest

from openai import OpenAI

from invariant.analyzer import Monitor

# define the policy to monitor the trace for security violations
monitor = Monitor.from_string(
    """
# check result after the operation
raise PolicyViolation("Invalid flow", a=call1, b=call2) if:
    (call1: ToolCall) -> (call2: ToolCall)
    call1 is tool:something
    call1.function.arguments["x"] > 10
    call2 is tool:something_else
""",
    raise_unhandled=True,
)

# create an OpenAI client
client = OpenAI()


def something(x: int):
    """Applies something() to the input value."""
    return x + 1


def something_else(x: int):
    """Applies something_else() to the input value."""
    return x * 2


def openai_agent():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "something",
                "description": "Computes something() of the input x.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                    },
                    "required": ["x"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "something_else",
                "description": "Computes something_else() of the input x.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                    },
                    "required": ["x"],
                },
            },
        },
    ]

    # Step 1: send the conversation and available functions to the model
    messages = [
        {
            "role": "user",
            "content": "What is something(4)? After you know, compute something_else() of the result.",
        }
    ]

    # Step 3: loop until the conversation is complete
    while True:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            tools=tools,
            tool_choice="auto",  # auto is default, but we'll be explicit
            parallel_tool_calls=False,
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        print(
            "Assistant:", response_message.content, "(tool_calls: {})".format(len(tool_calls or []))
        )

        # Step 2: check if the model wanted to call a function
        if tool_calls:
            available_functions = {
                "something": something,
                "something_else": something_else,
            }  # only one function in this example, but you can have multiple

            response_message = response_message.to_dict()

            # monitor for security violations
            monitor.check(messages, [response_message])
            messages.append(response_message)

            # Step 4: send the info for each function call and function response to the model
            pending_outputs = []
            for tool_call in tool_calls:
                print("Tool:", tool_call.function.name, tool_call.function.arguments)
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)

                function_response = function_to_call(
                    x=function_args.get("x"),
                )
                pending_outputs.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(function_response),
                    }
                )  # extend conversation with function response

            # again check for security violations
            monitor.check(messages, pending_outputs)
            messages.extend(pending_outputs)
        else:
            break

    last_message = messages[-1]
    assert "10" in last_message["content"] or "ten" in last_message["content"], (
        "Expected the final message to contain '10' or 'ten' but got: {}".format(
            last_message["content"]
        )
    )


class TestOpenAIAgentMonitoring(unittest.TestCase):
    def test_openai_agent_monitor(self):
        openai_agent()


if __name__ == "__main__":
    unittest.main()
