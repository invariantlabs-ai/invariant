"""Tests for the Trace class."""

import pytest

from invariant.testing import Trace


@pytest.fixture
def trace():
    return Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
            {"role": "assistant", "content": "Hi, how can I help you?"},
            {"role": "user", "content": "I need help with something."},
            {"role": "assistant", "content": "Sure, what do you need help with?"},
            {"role": "user", "content": "I need help with my computer."},
            {"role": "assistant", "content": "Okay, what seems to be the problem?"},
            {"role": "user", "content": "It won't turn on."},
            {"role": "assistant", "content": "Have you tried plugging it in?"},
            {"role": "user", "content": "Oh, that worked. Thanks!"},
        ]
    )


@pytest.fixture
def swarm_trace():
    return Trace(
        trace=[
            {
                "role": "user",
                "content": "How much time do I have to go to my lunch with Sarah on 2024-05-15? Give me the result in the format 'HH:MM'.",
            },
            {
                "content": None,
                "refusal": None,
                "role": "assistant",
                "audio": None,
                "function_call": None,
                "tool_calls": [
                    {
                        "id": "call_iL5lGunpRSNMgtNSdxnGRWjr",
                        "function": {
                            "arguments": '{"query":"Lunch with Sarah","date":"2024-05-15"}',
                            "name": "search_calendar_events",
                        },
                        "type": "function",
                    }
                ],
                "sender": "Agent A",
            },
            {
                "role": "tool",
                "tool_call_id": "call_iL5lGunpRSNMgtNSdxnGRWjr",
                "tool_name": "search_calendar_events",
                "content": "[{'title': 'Lunch with Sarah', 'date': '2024-05-15', 'time': '12:30', 'duration': '1:00'}]",
            },
            {
                "content": None,
                "refusal": None,
                "role": "assistant",
                "audio": None,
                "function_call": None,
                "tool_calls": [
                    {
                        "id": "call_JBViXjQT0UunZsKFZvPWvF5O",
                        "function": {
                            "arguments": '{"date": "2024-05-15"}',
                            "name": "search_calendar_events",
                        },
                        "type": "function",
                    },
                    {
                        "id": "call_k4QoRZEYzMed4QUhDS7tvyV6",
                        "function": {
                            "arguments": '{"date": "2024-05-14"}',
                            "name": "search_calendar_events",
                        },
                        "type": "function",
                    },
                ],
                "sender": "Agent A",
            },
            {
                "role": "tool",
                "tool_call_id": "call_JBViXjQT0UunZsKFZvPWvF5O",
                "tool_name": "search_calendar_events",
                "content": "[{'title': 'Meeting with John', 'date': '2024-05-15', 'time': '11:00', 'duration': '1:00'}, {'title': 'Lunch with Sarah', 'date': '2024-05-15', 'time': '12:30', 'duration': '1:00'}]",
            },
            {
                "role": "tool",
                "tool_call_id": "call_k4QoRZEYzMed4QUhDS7tvyV6",
                "tool_name": "search_calendar_events",
                "content": "[]",
            },
            {
                "content": "Your lunch with Sarah on 2024-05-15 is scheduled for 12:30 PM and it lasts for 1 hour. You have a meeting with John that day from 11:00 AM to 12:00 PM.\n\nTherefore, you have from 12:00 PM to 12:30 PM as free time before your lunch with Sarah. This gives you **00:30** minutes to transition between these events.",
                "refusal": None,
                "role": "assistant",
                "audio": None,
                "function_call": None,
                "tool_calls": None,
                "sender": "Agent A",
            },
        ]
    )


@pytest.fixture
def trace_with_tool_calls():
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


@pytest.fixture
def trace_with_images():
    return Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
            {
                "role": "assistant",
                "content": "Hello there",
            },
            {"role": "user", "content": "I need an image."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tool_1",
                        "type": "function",
                        "function": {
                            "name": "computer",
                            "arguments": {"action": "screenshot"},
                        },
                    }
                ],
            },
            {"id": "tool_1", "role": "tool", "content": "local_img_link: _some_url_"},
            {"role": "user", "content": "I need a different image"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tool_2",
                        "type": "function",
                        "function": {
                            "name": "computer",
                            "arguments": {"action": "screenshot"},
                        },
                    }
                ],
            },
            {"id": "tool_2", "role": "tool", "content": "local_base64_img: dGVzdA=="},
        ]
    )


@pytest.fixture
def trace_tool_call_with_duplicate_field():
    """Trace with a tool call that has the"""
    return Trace(
        trace=[
            {
                "role": "assistant",
                "content": "Hello there",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": "greet",
                            "arguments": {"name": "there"},
                            "duplicated_argument": "inner_value",
                        },
                        "duplicated_argument": "outer_value",
                    }
                ],
            },
        ]
    )


def test_messages_list_select(trace: Trace):
    assert trace.messages()[1]["content"].value == trace.trace[1]["content"]


def tests_messages_index_select(trace: Trace):
    assert trace.messages(1)["content"].value == trace.trace[1]["content"]


def test_messages_filter(trace: Trace):
    assert trace.messages(role="assistant")[0]["content"].value == "Hi, how can I help you?"


def test_messages_filter_callable(trace: Trace):
    assert (
        trace.messages(role=lambda r: r == "assistant")[0]["content"].value
        == "Hi, how can I help you?"
    )


def test_messages_filter_callable_user(trace: Trace):
    assert trace.messages(role=lambda r: r == "user")[0]["content"].value == "Hello there"


def test_messages_filter_callable_user_with_string_upper(trace: Trace):
    assert trace.messages(role=lambda r: r == "user")[0]["content"].upper() == "HELLO THERE"


def test_messages_filter_callable_user_with_string_lower(trace: Trace):
    assert trace.messages(role=lambda r: r == "user")[0]["content"].lower() == "hello there"


def test_messages_filter_callable_multiple(trace: Trace):
    assert (
        trace.messages(role=lambda r: r == "user", content=lambda c: "computer" in c)[0][
            "content"
        ].value
        == "I need help with my computer."
    )


def test_messages_filter_callable_multiple_2(trace: Trace):
    assert (
        trace.messages(role="user", content=lambda c: "computer" in c)[0]["content"].value
        == "I need help with my computer."
    )


def test_tool_calls(trace_with_tool_calls: Trace):
    tool_calls = trace_with_tool_calls.tool_calls()
    assert len(tool_calls) == 3


def test_tool_calls_filter(trace_with_tool_calls: Trace):
    tool_calls = trace_with_tool_calls.tool_calls(type="function")
    assert len(tool_calls) == 3


def test_tool_calls_filter_callable(trace_with_tool_calls: Trace):
    tool_calls = trace_with_tool_calls.tool_calls(function=lambda f: f["name"] == "greet")
    assert len(tool_calls) == 1


def test_tool_calls_filter_name(trace_with_tool_calls: Trace):
    tool_calls = trace_with_tool_calls.tool_calls(name="greet")
    assert len(tool_calls) == 1


def test_tool_calls_filter_name_callable(trace_with_tool_calls: Trace):
    tool_calls = trace_with_tool_calls.tool_calls(name=lambda n: n == "greet")
    assert len(tool_calls) == 1


def test_tool_calls_filter_name_callable_2(trace_with_tool_calls: Trace):
    tool_calls = trace_with_tool_calls.tool_calls(name=lambda n: "e" in n)
    assert len(tool_calls) == 2


def test_filter_on_image_returns_correct_number(trace_with_images: Trace):
    images = trace_with_images.messages(data_type="image")
    assert len(images) == 2

    images = trace_with_images.tool_outputs(data_type="image")
    assert len(images) == 2

    images = trace_with_images.tool_calls(data_type="image")
    assert len(images) == 0


def test_filter_on_image_returns_correct_image(trace_with_images: Trace):
    images = trace_with_images.messages(data_type="image")
    assert images[0]["id"] == "tool_1"
    assert images[1]["id"] == "tool_2"

    images = trace_with_images.tool_outputs(data_type="image")
    assert images[0]["id"] == "tool_1"
    assert images[1]["id"] == "tool_2"

    images = trace_with_images.tool_calls(data_type="image")
    assert len(images) == 0


@pytest.mark.parametrize("tool_id", ["tool_1", "tool_2"])
def test_filter_on_images_works_with_kw_selector(trace_with_images, tool_id):
    images = trace_with_images.tool_outputs(data_type="image", id=tool_id)
    assert images[0]["id"] == tool_id


@pytest.mark.parametrize("tool_id", ["tool_1", "tool_2"])
def test_filter_on_images_works_with_dict_selector(trace_with_images, tool_id):
    images = trace_with_images.tool_outputs(data_type="image", selector={"id": tool_id})
    assert images[0]["id"] == tool_id


def test_trace_with_nones(swarm_trace: Trace):
    """Test Swarm trace that could set tool calls to None and have extra arguments."""
    assert len(swarm_trace.messages()) == 7
    assert len(swarm_trace.messages(role="user")) == 1
    assert len(swarm_trace.tool_calls()) == 3
    assert len(swarm_trace.tool_calls(name="search_calendar_events")) == 3
    assert len(swarm_trace.tool_calls({"arguments.date": "2024-05-15"})) == 2
    assert len(swarm_trace.tool_calls({"arguments.command": "2024-05-15"})) == 0
    assert (
        len(
            swarm_trace.tool_calls(
                {"arguments.query": "Lunch with Sarah", "arguments.date": "2024-05-15"}
            )
        )
        == 1
    )
    assert len(swarm_trace.tool_pairs()) == 3


def test_dict_selector_with_and_without_function_dot(swarm_trace: Trace):
    """Test that dict selector on tool calls finds fields with and without function. prefix"""
    assert len(swarm_trace.tool_calls({"function.name": "search_calendar_events"})) == 3
    assert len(swarm_trace.tool_calls({"name": "search_calendar_events"})) == 3


def test_dict_selector_finds_top_field_for_tool_calls(
    trace_tool_call_with_duplicate_field: Trace,
):
    """Test that selector finds the first level field for tool calls
    and only checks nested structure if the field is not found.
    """
    assert (
        len(trace_tool_call_with_duplicate_field.tool_calls({"duplicated_argument": "outer_value"}))
        == 1
    )
    assert (
        len(
            trace_tool_call_with_duplicate_field.tool_calls(
                {"function.duplicated_argument": "inner_value"}
            )
        )
        == 1
    )


def test_tool_pairs():
    """Tests whether the tool pairs are extracted correctly."""
    trace = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "1",
                    "function": {"name": "func1", "arguments": {"arg1": "val1"}},
                },
                {
                    "id": "2",
                    "function": {"name": "func2", "arguments": {"arg2": "val2"}},
                },
            ],
        },
        {"role": "tool", "id": "1", "content": "Tool output 1"},
        {"role": "tool", "id": "2", "content": "Tool output 2"},
        {
            "role": "assistant",
            "tool_calls": [
                {"function": {"name": "func3", "arguments": {"arg3": "val3"}}},
            ],
        },
        {"role": "tool", "content": "Tool output 3"},
    ]
    tool_pairs = Trace(trace=trace).tool_pairs()
    assert len(tool_pairs) == 3
    assert tool_pairs[0][0]["id"] == "1" and tool_pairs[0][0]["function"]["name"] == "func1"
    assert tool_pairs[0][1]["id"] == "1" and tool_pairs[0][1]["content"] == "Tool output 1"
    assert tool_pairs[1][0]["id"] == "2" and tool_pairs[1][0]["function"]["name"] == "func2"
    assert tool_pairs[1][1]["id"] == "2" and tool_pairs[1][1]["content"] == "Tool output 2"
    assert tool_pairs[2][0]["function"]["name"] == "func3"
    assert tool_pairs[2][1]["content"] == "Tool output 3"
