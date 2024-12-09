"""Defines the expect functions."""

from typing import Any, Literal, Tuple

from invariant.custom_types.assertion_result import AssertionResult
from invariant.custom_types.invariant_bool import InvariantBool
from invariant.custom_types.invariant_value import InvariantValue
from invariant.custom_types.matchers import Matcher
from invariant.manager import Manager


def get_caller_snippet(levels=1) -> Tuple[str, int]:
    """Get the code snippet of the caller function."""
    import inspect  # pylint: disable=import-outside-toplevel

    # when called from e.g. assert_equals below, gets the full code of the caller function.
    frame = inspect.currentframe()
    caller_frame = frame.f_back
    # how many levels to traverse up to get to the caller
    for _ in range(levels):
        caller_frame = caller_frame.f_back
    fct = inspect.getframeinfo(caller_frame)
    # Check if called from the module level (not from a def)
    if fct.function == "<module>":
        caller_code = fct.code_context
        line_in_caller = 0
    else:
        caller_code = inspect.getsourcelines(caller_frame.f_code)[0]
        line_in_caller = fct.lineno - caller_frame.f_code.co_firstlineno
    marked_line = (
        caller_code[line_in_caller][1:]
        if caller_code[line_in_caller].startswith(" ")
        else caller_code[line_in_caller]
    )
    caller_code[line_in_caller] = f">{marked_line}"
    offset = max(0, line_in_caller - 5)
    line_in_snippet = line_in_caller - offset + 1
    caller_code = caller_code[offset : line_in_caller + 5]

    return "\n" + "".join(caller_code), line_in_snippet


def assert_equals(
    expected_value: InvariantValue,
    actual_value: InvariantValue,
    message: str = "",
    assertion_type: Literal["SOFT", "HARD"] = "HARD",
    stacklevels: int = 1,
):
    """Expect the invariant value to be equal to the given value."""
    # make sure lhs is an InvariantValue
    if not isinstance(actual_value, InvariantValue):
        actual_value = InvariantValue.of(actual_value, [])

    ctx = Manager.current()
    comparison_result = actual_value.equals(expected_value)

    test, testline = get_caller_snippet(levels=stacklevels)

    assertion = AssertionResult(
        passed=comparison_result.value,
        type=assertion_type,
        addresses=comparison_result.addresses,
        message=message
        + f" (expected: '{formatted(expected_value)}', actual: '{formatted(actual_value)}')",
        test=test,
        test_line=testline,
    )
    ctx.add_assertion(assertion)


def formatted(value: Any) -> str:
    """Format the value for display in an assertion message."""
    # For InvariantValue, get the actual value
    if isinstance(value, InvariantValue):
        value = value.value
    # For strings, unicode_escape them, so we can see special characters and don't render newlines
    if isinstance(value, str):
        value = value.encode("unicode_escape").decode()
    return str(value)


def expect_equals(
    expected_value: InvariantValue, actual_value: InvariantValue, message: str = ""
):
    """Expect the invariant value to be equal to the given value. This is a soft assertion."""
    assert_equals(
        expected_value,
        actual_value,
        message=message,
        assertion_type="SOFT",
        stacklevels=2,
    )


def assert_that(
    actual_value: InvariantValue,
    matcher: Matcher,
    message: str = None,
    assertion_type: Literal["SOFT", "HARD"] = "HARD",
    stacklevels: int = 1,
):
    """Expect the invariant value to match the given matcher."""
    ctx = Manager.current()
    comparison_result = actual_value.matches(matcher)

    test, testline = get_caller_snippet(levels=stacklevels)

    assertion = AssertionResult(
        passed=comparison_result.value,
        type=assertion_type,
        addresses=comparison_result.addresses,
        message=message,
        test=test,
        test_line=testline,
    )
    ctx.add_assertion(assertion)


def expect_that(actual_value: InvariantValue, matcher: Matcher, message: str = None):
    """Expect the invariant value to match the given matcher. This is a soft assertion."""
    assert_that(
        actual_value,
        matcher,
        message,
        "SOFT",
        stacklevels=2,
    )


def assert_true(
    actual_value: InvariantBool | bool,
    message: str = None,
    assertion_type: Literal["SOFT", "HARD"] = "HARD",
    stacklevels: int = 1,
):
    """Expect the actual_value to be true."""
    ctx = Manager.current()
    if isinstance(actual_value, InvariantBool):
        comparison_result = actual_value.value
        addresses = actual_value.addresses
    else:
        comparison_result = actual_value
        addresses = []

    test, testline = get_caller_snippet(levels=stacklevels)

    assertion = AssertionResult(
        passed=comparison_result,
        type=assertion_type,
        addresses=addresses,
        message=message,
        test=test,
        test_line=testline,
    )
    ctx.add_assertion(assertion)


def expect_true(
    actual_value: InvariantBool | bool,
    message: str = None,
):
    """Expect the actual_value to be true. This is a soft assertion."""
    assert_true(
        actual_value,
        message,
        "SOFT",
        stacklevels=2,
    )


def assert_false(
    actual_value: InvariantBool | bool,
    message: str = None,
    assertion_type: Literal["SOFT", "HARD"] = "HARD",
    stacklevels: int = 1,
):
    """Expect the actual_value to be false."""
    ctx = Manager.current()
    if isinstance(actual_value, InvariantBool):
        comparison_result = not actual_value.value
        addresses = actual_value.addresses
    else:
        comparison_result = not actual_value
        addresses = []

    test, testline = get_caller_snippet(levels=stacklevels)

    assertion = AssertionResult(
        passed=comparison_result,
        type=assertion_type,
        addresses=addresses,
        message=message,
        test=test,
        test_line=testline,
    )
    ctx.add_assertion(assertion)


def expect_false(
    actual_value: InvariantBool | bool,
    message: str = None,
):
    """Expect the actual_value to be false. This is a soft assertion."""
    assert_false(
        actual_value,
        message,
        "SOFT",
        stacklevels=2,
    )
