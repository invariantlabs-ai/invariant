"""Contains sample tests which use the Invariant Runner."""

import pytest
from invariant.testing import (
    HasSubstring,
    Trace,
    assert_equals,
    assert_that,
    assert_true,
    expect_equals,
)


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


def is_similar_to(expected: str, threshold: float = 0.8):
    pass


def test_another_agent_response():
    """Test another agent response."""
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])

    with trace.as_context():
        expect_equals(
            "Hello three",
            trace.messages()[0]["content"],
            "First message should greet 'three'",
        )
        expect_equals(
            "What's Up?",
            trace.messages()[0]["content"],
            "First message should greet 'What's Up?'",
        )
        assert_equals(
            "Hello three",
            trace.messages()[0]["content"].len(),
            "First message should greet 'three'",
        )
        assert_that(
            trace.messages()[0]["content"],
            HasSubstring("hsfa"),
            "First message should match 'hsfa'",
        )


@pytest.fixture
def big_trace():
    return Trace(
        trace=[
            {
                "role": "user",
                "content": "Could you kindly show me the list of files in tmp directory in my file system including the hidden one?",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_ls7AnBVJzZQPHTrKg0G7",
                        "type": "function",
                        "function": {"name": "cd", "arguments": {"folder": "tmp"}},
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"error": "cd: tmp: No such directory. You cannot use path to change directory."}',
                "tool_call_id": "call_ls7AnBVJzZQPHTrKg0G7",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_6DKFVzXQkTT0fTUDy7lw",
                        "type": "function",
                        "function": {"name": "ls", "arguments": {"a": True}},
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"current_directory_content": ["report.txt"]}',
                "tool_call_id": "call_6DKFVzXQkTT0fTUDy7lw",
            },
            {
                "role": "assistant",
                "content": "In the current directory, there is one file: **report.txt**. There are no hidden files listed.",
            },
            {
                "role": "user",
                "content": "There is a report in my current directory. I have noticed the report appears somewhat cluttered; it could benefit from having its lines sorted.",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_QxxWLVviOvv7XXrXLxoN",
                        "type": "function",
                        "function": {
                            "name": "sort",
                            "arguments": {"file_name": "report.txt"},
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"sorted_content": "Initial report content Unsorted data More unsorted data"}',
                "tool_call_id": "call_QxxWLVviOvv7XXrXLxoN",
            },
            {
                "role": "assistant",
                "content": "The lines in **report.txt** have been sorted. The sorted content is as follows:\n\n```\nInitial report content\nMore unsorted data\nUnsorted data\n``` \n\nIf you need any further modifications or actions, feel free to ask!",
            },
            {
                "role": "user",
                "content": "I would appreciate it if you could share the sorted result as the message body on social media, ensuring to tag 'currenttechtrend' and mention Julia, our insightful team.",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_heZY5J5gObsexwC6CTcu",
                        "type": "function",
                        "function": {
                            "name": "post_tweet",
                            "arguments": {
                                "content": "Initial report content\nMore unsorted data\nUnsorted data",
                                "tags": [],
                                "mentions": ["@currenttechtrend", "@Julia"],
                            },
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"id": 2, "username": "tech_guru", "content": "Initial report content\\nMore unsorted data\\nUnsorted data", "tags": [], "mentions": ["@currenttechtrend", "@Julia"]}',
                "tool_call_id": "call_heZY5J5gObsexwC6CTcu",
            },
            {
                "role": "assistant",
                "content": "The sorted report has been successfully posted on social media. Here are the details:\n\n- **Content:** \n  ```\n  Initial report content\n  More unsorted data\n  Unsorted data\n  ```\n- **Mentions:** @currenttechtrend, @Julia\n\nIf there's anything else you need, just let me know!",
            },
        ]
    )


def test_big_trace(big_trace: Trace):
    """Test trace with tool calls."""
    trace = Trace(
        trace=[
            {
                "role": "user",
                "content": "Could you kindly show me the list of files in tmp directory in my file system including the hidden one?",
            },
            {
                "role": "assistant",
                "content": "In the current directory, there is one file: **report.txt**. There are no hidden files listed.",
            },
        ]
    )

    with trace.as_context():
        for tc in trace.messages(role="assistant"):
            assert_true(
                tc["content"].contains("current"),
                "Assistant message content should contain the word 'current'",
            )


def test_trace_rules(trace_with_tool_calls: Trace):
    """Test trace rules."""
    with trace_with_tool_calls.as_context():
        tool_calls_with_greet = trace_with_tool_calls.tool_calls(
            name=lambda n: n == "greet"
        )
        assert_true(tool_calls_with_greet[0]["function"]["name"] == "greet")

        tool_calls_with_ask = trace_with_tool_calls.tool_calls(
            name=lambda n: n == "ask"
        )
        assert_true(tool_calls_with_ask[0].argument("question").contains("help"))
        assert_true(not tool_calls_with_ask[0].argument("question").contains("helpp"))

        assistant_messages = trace_with_tool_calls.messages(role="assistant")
        assert len(assistant_messages) == 2
        assert_equals(
            "Hello there",
            assistant_messages[0]["content"],
            "First message should greet 'there'",
        )
        assert_equals(
            "I need help with something",
            assistant_messages[1]["content"],
            "Second message should greet 'something'",
        )


def test_custom_trace():
    trace = Trace(
        trace=[
            {"role": "user", "content": "what's the weather in bern?"},
            {
                "content": "",
                "role": "assistant",
                "sender": "Agent A",
                "tool_calls": [
                    {
                        "id": "call_WqAaSNVKa8Ii5nD3EaNlJqsW",
                        "function": {"arguments": "{}", "name": "transfer_to_agent_b"},
                        "type": "function",
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_WqAaSNVKa8Ii5nD3EaNlJqsW",
                "tool_name": "transfer_to_agent_b",
                "content": '{"assistant": "Agent B"}',
            },
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_qbPWQHy8pwQEjuAdnRzR7qEj",
                        "function": {
                            "arguments": '{"lat": "46.948", "lon": "7.4474"}',
                            "name": "get_weather",
                        },
                        "type": "function",
                    }
                ],
                "sender": "Agent B",
            },
            {
                "role": "tool",
                "tool_call_id": "call_qbPWQHy8pwQEjuAdnRzR7qEj",
                "tool_name": "get_weather",
                "content": "{'coord': {'lon': 7.4515, 'lat': 46.9483}, 'weather': [{'id': 803, 'main': 'Clouds', 'description': 'broken clouds', 'icon': '04d'}], 'base': 'stations', 'main': {'temp': 272.86, 'feels_like': 272.86, 'temp_min': 270.7, 'temp_max': 273.4, 'pressure': 1011, 'humidity': 78, 'sea_level': 1011, 'grnd_level': 935}, 'visibility': 10000, 'wind': {'speed': 0.89, 'deg': 212, 'gust': 1.79}, 'clouds': {'all': 73}, 'dt': 1732172700, 'sys': {'type': 2, 'id': 2012960, 'country': 'CH', 'sunrise': 1732171347, 'sunset': 1732204211}, 'timezone': 3600, 'id': 2661552, 'name': 'Bern', 'cod': 200}",
            },
            {
                "content": "Clouds hover above,  \nIn beautiful Bern today,  \nChilly air whispers.",
                "role": "assistant",
                "sender": "Agent B",
            },
        ]
    )
    with trace.as_context():
        assert_true(trace.messages(role="assistant")[0]["sender"] == "Agent A")

        # assert 3 lines in the last message
        res = trace.messages(role="assistant")[-1]["content"].count("\n")
        assert_true(res == 2)
        assert (
            len(res.addresses) == 2
            and res.addresses[0] == "5.content:21-22"
            and res.addresses[1] == "5.content:48-49"
        )

        # tool call names
        tool_calls = trace.tool_calls()
        assert_true(tool_calls[0]["function"]["name"] == "transfer_to_agent_b")
        assert_true(tool_calls[1]["function"]["name"] == "get_weather")

        # single index
        res = tool_calls[1].argument()[19]
        assert_true(res == "l")
        assert (
            len(res.addresses) == 1
            and res.addresses[0] == "3.tool_calls.0.function.arguments:19-20"
        )

        # slice
        res = tool_calls[1].argument()[19:22]
        assert_true(res == "lon")
        assert (
            len(res.addresses) == 1
            and res.addresses[0] == "3.tool_calls.0.function.arguments:19-22"
        )

        # json parameters
        assert_true(tool_calls[1].argument().is_valid_code("json"))
        assert_true(tool_calls[1].argument("lat") == "46.948")
        assert_true(tool_calls[1].argument("lon") == "7.4474")


@pytest.mark.parametrize(
    "name, bool1", [("Alice", True), ("Alice", False), ("Bob", False), ("Bob", True)]
)
def test_get_test_name_and_parameters_from_request(
    request, name, bool1, trace_with_tool_calls
):
    """Test get_test_name_and_parameters."""
    with trace_with_tool_calls.as_context():
        pass


@pytest.mark.parametrize(
    "name, bool1",
    [("Jacob", True), ("Jacob", False), ("Alfred", False), ("Alfred", True)],
)
def test_get_test_name_and_parameters_from_env(name, bool1, trace_with_tool_calls):
    """Test get_test_name_and_parameters."""
    with trace_with_tool_calls.as_context():
        pass


def test_something():
    """Test something."""
    # create a Trace object from your agent trajectory
    trace = Trace(
        trace=[
            {"role": "user", "content": "What is the weather like in Paris?"},
            {"role": "agent", "content": "The weather in Paris is 75°F and sunny."},
        ]
    )

    # make assertions about the agent's behavior
    with trace.as_context():
        assert_true(
            trace.messages(-1)["content"].contains("Paris"),
            "The agent should respond about Paris",
        )
