import invariant.testing.functional as F
from invariant.testing import Trace, assert_true
from invariant.tests.testing.testutils import should_fail_with


@should_fail_with(num_assertion=1)
def test_in():
    """Test that expect_equals works fine with the right order."""
    trace = Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
            {"role": "assistant", "content": "there where!?"},
            {"role": "assistant", "content": "Hello to you as well"},
        ]
    )

    with trace.as_context():
        assert_true(F.len(trace.messages(content=lambda c: "Hello" in c)) == 3)
        assert_true(F.len(trace.messages(content=lambda c: "there" in c)) == 2)


@should_fail_with(num_assertion=1)
def test_in_word_level():
    """Test that expect_equals works fine with the right order."""
    trace = Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
            {"role": "assistant", "content": "there where!?"},
            {"role": "assistant", "content": "Hello to you as well"},
        ]
    )

    with trace.as_context():
        trace.messages(content=lambda c: "Hello" in c)
        hellos = [msg["content"].contains("Hello") for msg in trace.messages()]
        theres = [msg["content"].contains("there") for msg in trace.messages()]
        assert_true(
            F.len([x for x in hellos if x]) == 3,
            "Expected 3 messages to contain 'Hello'",
        )
        assert_true(
            F.len([x for x in theres if x]) == 2,
            "Expected 2 messages to contain 'there'",
        )
