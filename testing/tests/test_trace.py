import pytest

from invariant.custom_types.trace import Trace
from invariant.custom_types.invariant_dict import InvariantDict

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

    assert trace.messages(-1).value == {"role": "user", "content": "I need help with my computer."}
    assert trace.messages(-1).addresses == ["4"]
    assert trace.messages(0) == trace.messages(-5)

    with pytest.raises(IndexError):
        trace.messages(-10)
        trace.messages(-5)
        trace.messages(5)

