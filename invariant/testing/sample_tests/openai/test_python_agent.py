import json
from unittest.mock import MagicMock

import invariant.testing.functional as F
import openai
from invariant.testing import TraceFactory, assert_true, expect_equals


def run_python(code):
    import sys
    from io import StringIO

    stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        exec(code)
        output = sys.stdout.getvalue()
    except Exception as e:
        output = str(e)
    finally:
        sys.stdout = stdout
    return output


tools = [
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Run the provided snippet of Python code",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to run",
                    },
                },
                "required": ["code"],
            },
        },
    }
]


class PythonAgent:
    """An openai agent that run Python code fulfilling the user's request."""

    def __init__(self):
        self.client = openai.OpenAI()
        self.prompt = """
                        You are an assistant that strictly responds with Python code only. 
                        The code should print the result.
                        You always use tool run_python to execute the code that you write to present the results.
                        If the user specifies other programming language in the question, you should respond with "I can only help with Python code."
                    """

    def get_response(self, user_input: str):
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": user_input},
        ]

        while True:
            response = self.client.chat.completions.create(
                messages=messages,
                model="gpt-4o",
                tools=tools,
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            if tool_calls:
                response_message = response_message.to_dict()
                messages.append(response_message)
                # In this demo there's only one tool call in the response
                tool_call = tool_calls[0]
                if tool_call.function.name == "run_python":
                    function_args = json.loads(tool_call.function.arguments)
                    function_response = run_python(function_args["code"])
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "run_python",
                            "content": str(function_response),
                        }
                    )
            else:
                break
        messages.append(response.choices[0].message.to_dict())
        return messages


# This is a test that the agent should execute valid python code and get result for a question about fibonacci series
def test_python_question():
    input = "Calculate fibonacci series for the first 10 elements in python"
    python_agent = PythonAgent()
    response = python_agent.get_response(input)
    trace = TraceFactory.from_openai(response)
    with trace.as_context():
        run_python_tool_call = trace.tool_calls(name="run_python")
        assert_true(F.len(run_python_tool_call) == 1)
        assert_true(run_python_tool_call[0].argument("code").is_valid_code("python"))
        assert_true("34" in trace.messages(-1)["content"])


# This is a test that mock the agent respond with Java code
def test_python_question_invalid():
    input = "Calculate fibonacci series for the first 10 elements in python"
    python_agent = PythonAgent()
    mock_invalid_response = [
        {
            "role": "system",
            "content": '\n                    You are an assistant that strictly responds with Python code only. \n                    The code should print the result.\n                    You always use tool run_python to execute the code that you write to present the results.\n                    If the user specifies other programming language in the question, you should respond with "I can only help with Python code."\n                    ',
        },
        {"role": "user", "content": "Calculate fibonacci series for 10"},
        {
            "content": "None",
            "refusal": "None",
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_GMx1WYM7sN0BGY1ISCk05zez",
                    "function": {
                        "arguments": '{"code":"public class Fibonacci { public static void main(String[] args) { for (int n = 10, a = 0, b = 1, i = 0; i < n; i++, b = a + (a = b)) System.out.print(a + '
                        '); } }"}',
                        "name": "run_python",
                    },
                    "type": "function",
                }
            ],
        },
    ]
    python_agent.get_response = MagicMock(return_value=mock_invalid_response)
    response = python_agent.get_response(input)
    trace = TraceFactory.from_openai(response)
    with trace.as_context():
        run_python_tool_call = trace.tool_calls(name="run_python")
        assert_true(F.len(run_python_tool_call) == 1)
        assert_true(
            not run_python_tool_call[0].argument("code").is_valid_code("python")
        )


#  This is a test that the request specifies another programming language Java
#  The agent should respond with "I can only help with Python code."
def test_java_question():
    input = "How to calculate fibonacci series in Java?"
    python_agent = PythonAgent()
    response = python_agent.get_response(input)
    trace = TraceFactory.from_openai(response)
    expected_response = "I can only help with Python code."
    with trace.as_context():
        run_python_tool_call = trace.tool_calls(name="run_python")
        assert_true(F.len(run_python_tool_call) == 0)
        expect_equals(expected_response, trace.messages(-1)["content"])

        assert_true(trace.messages(-1)["content"].levenshtein(expected_response) < 5)
