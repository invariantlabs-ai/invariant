"""Test the naming of tests which are used in our summaries and pushed to explorer."""

from unittest.mock import patch

import pytest

from invariant.testing import Trace, assert_true

# pylint: disable=protected-access


def test_my_test():
    """Test that the test name is correctly set."""
    trace = Trace(trace=[{"role": "user", "content": "Hello, world!"}])

    with patch("invariant.testing.manager.Manager.handle_outcome") as mock_handle_outcome:
        mock_handle_outcome.return_value = None

        with trace.as_context() as mgr:
            assert_true(True)

        assert mgr._get_test_result().name == "test_my_test", (
            "Expected test name to be 'test_my_test'"
        )


@pytest.mark.parametrize("value", ["hello"])
def test_param(value):
    """Test that the test name is correctly set when a parameter is passed."""
    trace = Trace(trace=[{"role": "user", "content": value}])

    with patch("invariant.testing.manager.Manager.handle_outcome") as mock_handle_outcome:
        mock_handle_outcome.return_value = None

        with trace.as_context() as mgr:
            assert_true(True)

        assert mgr._get_test_result().name == "test_param[hello]", (
            "Expected test name to be 'test_param[hello]'"
        )


@pytest.mark.parametrize("value", ["hello there"])
def test_param_with_spaces(value):
    """Test that test names with spaces are handled correctly."""
    trace = Trace(trace=[{"role": "user", "content": value}])

    with patch("invariant.testing.manager.Manager.handle_outcome") as mock_handle_outcome:
        mock_handle_outcome.return_value = None

        with trace.as_context() as mgr:
            assert_true(True)

        assert mgr._get_test_result().name == "test_param_with_spaces[hello there]", (
            "Expected test name to be 'test_param_with_spaces[hello there]'"
        )


@pytest.mark.parametrize("value", ["hello :: there"])
def test_param_with_colons(value):
    """Test that test names with colons are handled correctly."""
    trace = Trace(trace=[{"role": "user", "content": value}])

    with patch("invariant.testing.manager.Manager.handle_outcome") as mock_handle_outcome:
        mock_handle_outcome.return_value = None

        with trace.as_context() as mgr:
            assert_true(True)

        assert mgr._get_test_result().name == "test_param_with_colons[hello :: there]", (
            "Expected test name to be 'test_param_with_colons[hello :: there]'"
        )
