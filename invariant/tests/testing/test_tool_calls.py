import pytest

import invariant.testing.functional as F
from invariant.testing import Trace, assert_true


@pytest.fixture(name="trace_with_tool_calls")
def fixture_tool_call_list():
    """Returns a trace includes a response includes multiple tool calls."""
    response = [
        {
            "role": "system",
            "content": 'in the question, you should respond with "I can only help with Python code."\n',
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
                        "arguments": '{"code":"System.out.print(a + b)"}',
                        "name": "run_python",
                    },
                    "type": "function",
                }
            ],
        },
        {
            "content": "None",
            "refusal": "None",
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_GMx1WYM7sN0BGY1ISCk05zez",
                    "function": {
                        "weird_argument": '{"code":"System.out.print(a + b)"}',
                        "name": "run_python",
                    },
                    "type": "tool",
                }
            ],
        },
        {
            "content": "None",
            "refusal": "None",
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_GMx1WYM",
                    "function": {
                        "arguments": {
                            "code": {
                                "text": "System.out.print(a + b)",
                                "language": "java",
                            },
                        },
                        "name": "run_python",
                    },
                    "type": "tool",
                }
            ],
        },
    ]
    trace = Trace(trace=response)
    return trace


def test_argument(trace_with_tool_calls):
    with trace_with_tool_calls.as_context():
        run_python_tool_call = trace_with_tool_calls.tool_calls({"name": "run_python"})

        assert_true(F.len(run_python_tool_call) == 3)

        assert_true(run_python_tool_call[0].argument("code").is_valid_code("python"))

        assert_true(
            run_python_tool_call[0].argument()[0]
            == run_python_tool_call[0]["function"]["arguments"][0]
        )

        assert_true(
            run_python_tool_call[1].argument("function.weird_argument.code").is_valid_code("python")
        )

        assert_true(
            run_python_tool_call[2].argument("code")
            == run_python_tool_call[2]["function"]["arguments"]["code"]
        )
        assert_true(
            run_python_tool_call[2].argument("code.text")
            == run_python_tool_call[2]["function"]["arguments"]["code"]["text"]
        )
        assert_true(
            run_python_tool_call[2].argument("function.arguments.code.language")
            == run_python_tool_call[2]["function"]["arguments"]["code"]["language"]
        )

        with pytest.raises(KeyError):
            run_python_tool_call[0].argument("pyto")
            run_python_tool_call[2].argument("code.does_not_exist")
            run_python_tool_call[2].argument("does_not_exist")

        with pytest.raises(ValueError):
            trace_with_tool_calls.messages(role="user")[0].argument("content")
            run_python_tool_call[1].argument("code")

        with pytest.raises(TypeError):
            run_python_tool_call[0].argument(1)
