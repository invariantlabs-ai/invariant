"""Checks that flipping the order of (expected, actual) on _equals assertions and
expectations does not crash the test.
"""

from invariant.testing import Trace, assert_equals, expect_equals
from invariant.tests.testing.testutils import should_fail_with


@should_fail_with(num_assertion=1)
def test_wrong_order():
    """Test that flipping (expected, actual) on _equals assertions does not crash the test."""
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])

    with trace.as_context():
        assert_equals(trace.messages(0)["content"], "abc")


@should_fail_with(num_assertion=1)
def test_right_order():
    """Test that assert_equals works fine with the right order."""
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])

    with trace.as_context():
        assert_equals("abc", trace.messages(0)["content"])


@should_fail_with(num_assertion=0)
def test_expect_wrong_order():
    """Test that flipping (expected, actual) on _equals expectations does not crash the test."""
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])

    with trace.as_context():
        expect_equals(trace.messages(0)["content"], "abc")


@should_fail_with(num_assertion=0)
def test_expect_right_order():
    """Test that expect_equals works fine with the right order."""
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])

    with trace.as_context():
        expect_equals("abc", trace.messages(0)["content"])
