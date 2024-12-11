import pytest

from invariant.custom_types.trace import Trace, traverse_dot_path


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
