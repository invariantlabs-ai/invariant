import pytest

from invariant.testing import Trace


@pytest.fixture(name="trace_with_tool_calls")
def trace_with_tool_calls_fixture():
    """Return a trace with tool calls."""
    return Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
            {
                "role": "assistant",
                "content": "Hello there",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {"name": "greet", "arguments": {"name": "there"}},
                    }
                ],
            },
            {"role": "user", "content": "I need help with something."},
            {
                "role": "assistant",
                "content": "I need help with something",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": "help",
                            "arguments": {"thing": "something"},
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "ask",
                            "arguments": {"question": "what do you need help with?"},
                        },
                    },
                ],
            },
        ]
    )


def test_trace_complex_agent(trace_with_tool_calls: Trace):
    # make sure the context manager does not hide the exception
    with pytest.raises(NotImplementedError):
        with trace_with_tool_calls.as_context():
            raise NotImplementedError("Not implemented")
