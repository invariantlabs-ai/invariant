import invariant.testing.functional as F
from invariant.testing import Trace, assert_true


def test_assertion_points_to_substring():
    """Test to display how addresses pointing to substr of content."""
    trace = Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
        ]
    )
    with trace.as_context():
        assert_true(
            trace.messages()[0]["content"].contains("Hello"),
            "Expected Hello to be in the first message",
        )


def test_assertion_points_to_message_content_string():
    """Test to display how addresses pointing to message with content which is a str."""
    trace = Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
        ]
    )
    with trace.as_context():
        assert_true(
            F.len(trace.messages()) == 1,
            "Expected to have exactly one message",
        )


def test_assertion_points_to_message_content_dict():
    """Test to display how addresses pointing to message with content which is a dict."""
    trace = Trace(
        trace=[
            {"role": "user", "content": {"this": "is", "a": "dictionary"}},
        ]
    )
    with trace.as_context():
        assert_true(
            F.len(trace.messages()) == 1,
            "Expected to have exactly one message",
        )


def test_assertion_points_to_message_tool_call():
    """Test to display how addresses pointing to message composed only of tool calls are displayed."""
    trace = Trace(
        trace=[
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_uB9tU43cqiiE1CyYzrg7b07b",
                        "function": {
                            "arguments": '{"query":"lunch with Sarah","date":"2024-05-15"}',
                            "name": "search_calendar_events",
                        },
                        "type": "function",
                    },
                    {
                        "id": "call_uB9tU43cqiiE1CyYzrg7b07b",
                        "function": {
                            "arguments": '{"query":"lunch with Sarah","date":"2024-05-15"}',
                            "name": "search_calendar_events",
                        },
                        "type": "function",
                    },
                ],
            },
        ]
    )
    with trace.as_context():
        assert_true(
            F.len(trace.messages()) == 1,
            "Expected to have exactly one message",
        )


def test_assertion_points_to_tool_call():
    """Test to display how addresses pointing to tool call are displayed."""
    trace = Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
            {
                "role": "assistant",
                "content": {
                    "option1": "there where!?",
                    "option2": "Hello to you as well",
                    "Hello": "Hello to you as well",
                    "there": {"there": "Hello to you as well"},
                },
            },
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_uB9tU43cqiiE1CyYzrg7b07b",
                        "function": {
                            "arguments": '{"query":"lunch with Sarah","date":"2024-05-15"}',
                            "name": "tool_1",
                        },
                        "type": "function",
                    },
                    {
                        "id": "call_uB9tU43cqiiE1CyYzrg7b07b",
                        "function": {
                            "arguments": '{"query":"lunch with Sarah","date":"2024-05-15"}',
                            "name": "tool_2",
                        },
                        "type": "function",
                    },
                ],
            },
        ]
    )

    with trace.as_context():
        assert_true(F.len(trace.tool_calls(name="tool_2")) == 1)
