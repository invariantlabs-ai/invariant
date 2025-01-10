from unittest.mock import patch

import pytest
from invariant_sdk.client import Client as InvariantClient
from invariant_sdk.types.push_traces import PushTracesRequest

from invariant.testing.custom_types.trace import Trace, traverse_dot_path


@pytest.fixture(name="sample_trace")
def sample_trace_fixture() -> Trace:
    """Sample trace fixture."""
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
        ],
        metadata={"interisting": "very much"},
    )


class MockException(Exception):
    pass


def mocked_request(self, method, pathname, request_kwargs):
    """Check that the request kwargs match a PushTracesRequest.

    Raise MockException if successful. This way we prevent code executing after the request call from breaking.
    """
    PushTracesRequest(**request_kwargs["json"])
    raise MockException("This is Mocked")


def test_push_to_explorer(sample_trace: Trace):
    """Testing push to explorer method. Test only if the requests is well formed."""
    client = InvariantClient(api_key="fake_url", api_url="http://fake_key")
    with patch("invariant_sdk.client.Client.request", mocked_request):
        try:
            sample_trace.push_to_explorer(client=client)
        except MockException:
            # The mocked request returned MockException if everything went fine, else the test fails
            pass


@pytest.fixture(name="message_list")
def fixture_message_list():
    """Returns a list of messages."""
    trace = Trace(
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
    return trace.messages()


@pytest.fixture(name="dict_traversal")
def fixture_for_dict_traversal():
    return {
        "user": {"name": "Alice", "details": {"age": 30, "email": "alice@example.com"}},
        "function": {"tool_calls": {"name": "example_tool", "status": "success"}},
    }


def test_trace_iterable(message_list: Trace):
    trace = message_list

    for message in trace:
        assert message in trace


def test_trace_iterable_maintains_order(message_list: Trace):
    trace = message_list

    for i, message in enumerate(trace):
        assert message == trace[i]


def test_trace_messages_with_index():
    trace = Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
            {"role": "assistant", "content": "Hi, how can I help you?"},
            {"role": "user", "content": "I need help with something."},
            {"role": "assistant", "content": "Sure, what do you need help with?"},
            {"role": "user", "content": "I need help with my computer."},
        ]
    )

    assert trace.messages(-1).value == {
        "role": "user",
        "content": "I need help with my computer.",
    }
    assert trace.messages(-1).addresses == ["4"]
    assert trace.messages(0) == trace.messages(-5)

    with pytest.raises(IndexError):
        trace.messages(-10)
        trace.messages(-5)
        trace.messages(5)


def test_traverse_dot_path_found_match(dict_traversal):
    value, prefix_added = traverse_dot_path(dict_traversal, "user.details.email")
    assert value == "alice@example.com"
    assert not prefix_added


def test_traverse_dot_path_no_found_match_with_function_prefix(dict_traversal):
    value, prefix_added = traverse_dot_path(dict_traversal, "user.details.phone")
    assert value is None
    assert prefix_added  # Because function prefix was attempted.


def test_traverse_dot_path_found_match_with_function_prefix(dict_traversal):
    value, prefix_added = traverse_dot_path(dict_traversal, "tool_calls.name")
    assert value == "example_tool"
    assert prefix_added  # Because function prefix was attempted.


def test_traverse_dot_path_testing_none():
    dict1 = {"user": None}
    value, prefix_added = traverse_dot_path(dict1, "user.details")
    assert value is None
    assert prefix_added  # Because function prefix was attempted.
