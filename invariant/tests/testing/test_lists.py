"""Tests for the invariant list functions."""

import pytest

import invariant.testing.functional as F
from invariant.testing import Trace
from invariant.testing.custom_types.invariant_bool import InvariantBool
from invariant.testing.custom_types.invariant_number import InvariantNumber
from invariant.testing.custom_types.invariant_string import InvariantString


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


@pytest.fixture(name="simple_trace")
def fixture_simple_trace():
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
    return trace


@pytest.fixture(name="invariant_number_list")
def fixture_invariant_number_list():
    """Returns a list of InvariantNumber objects."""
    return [
        InvariantNumber(1, addresses=["0"]),
        InvariantNumber(5, addresses=["1"]),
        InvariantNumber(8, addresses=["2"]),
        InvariantNumber(4, addresses=["3"]),
        InvariantNumber(2, addresses=["4"]),
        InvariantNumber(4, addresses=["5"]),
    ]


@pytest.fixture(name="invariant_string_list")
def fixture_invariant_string_list():
    """Returns a list of InvariantString objects."""
    return [
        InvariantString("1", addresses=["0"]),
        InvariantString("12", addresses=["1"]),
        InvariantString("123", addresses=["2"]),
    ]


@pytest.fixture(name="invariant_bool_list")
def fixture_invariant_bool_list():
    """Returns a list of InvariantBool objects."""
    return [
        InvariantBool(True, addresses=["0"]),
        InvariantBool(False, addresses=["1"]),
        InvariantBool(True, addresses=["2"]),
    ]


def test_list_index_access(message_list: list):
    """Test that we can access elements in the list by index."""
    assert message_list[1]["content"].value == "Hi, how can I help you?"


def test_list_length(message_list: list):
    """Test that the list has the correct length."""
    assert len(message_list) == 9


def test_list_iteration(message_list: list):
    """Test that we can iterate over the list."""
    for i, message in enumerate(message_list):
        assert message["content"].value == message_list[i]["content"].value


def test_map_applies_function(message_list: list):
    """Test that the map function applies a function to each element in the list."""
    test_message_content = message_list[1]["content"].value
    new_list = F.map(lambda item: item["content"] == test_message_content, message_list)

    for i, new_item in enumerate(new_list):
        assert new_item.value == (message_list[i]["content"].value == test_message_content)


def test_map_maintains_addresses(message_list: list):
    """Test that the map function maintains addresses when applying a function."""
    new_list = F.map(lambda item: item, message_list)

    for i, new_item in enumerate(new_list):
        assert new_item.addresses == message_list[i].addresses


def test_reduce(invariant_number_list: list):
    """Test that the reduce function works."""
    sum_of_list = 0
    for item in invariant_number_list:
        sum_of_list += item.value

    reduced = F.reduce(lambda a, b: a + b, 0, invariant_number_list)

    assert reduced.value == sum_of_list
    assert isinstance(reduced, InvariantNumber)


def test_reduce_raw(invariant_number_list: list):
    """Test that the reduce_raw returns the correct value and removes address information."""
    sum_of_list = 0
    for item in invariant_number_list:
        sum_of_list += item.value

    reduced = F.reduce_raw(lambda a, b: a + b, 0, invariant_number_list)

    assert reduced == sum_of_list
    assert isinstance(reduced, int)


def test_min_helper(invariant_number_list: list):
    """Test that the min helper correct value and only keeps one address."""
    min_of_list = min([item.value for item in invariant_number_list])
    min_value = min(invariant_number_list)

    assert min_value.value == min_of_list
    assert len(min_value.addresses) == 1


def test_max_helper(invariant_number_list: list):
    """Test that the max helper returns correct value and only keeps one address."""
    max_of_list = max([item.value for item in invariant_number_list])

    max_value = max(invariant_number_list)

    assert max_value.value == max_of_list
    assert len(max_value.addresses) == 1


def test_sum_helper(invariant_number_list: list):
    """Test that the sum helper returns correct value and keeps all addresses."""
    sum_of_list = sum([item.value for item in invariant_number_list])
    sum_value = sum(invariant_number_list)

    assert isinstance(sum_value, InvariantNumber)
    assert sum_value.value == sum_of_list
    assert len(sum_value.addresses) == len(invariant_number_list)


def test_count_helper_with_value(invariant_string_list: list):
    """Test that the count helper returns correct value and keeps all addresses."""
    string_to_count = "12"

    count_value = F.count(string_to_count, invariant_string_list)
    real_count = sum([1 if item.value == string_to_count else 0 for item in invariant_string_list])

    assert isinstance(count_value, InvariantNumber)
    assert count_value.value == real_count
    assert len(count_value.addresses) == len(invariant_string_list)


def test_count_helper_with_lambda(invariant_number_list: list):
    """Test that the count function works with lambda."""
    result = F.count(lambda v: v == 1, invariant_number_list)
    assert result == InvariantNumber(1)
    assert result.addresses == [v.addresses[0] for v in invariant_number_list]


def test_any_helper(invariant_bool_list: list):
    """Test that the any helper returns correct value and keeps all addresses."""
    any_value = F.any(invariant_bool_list)

    assert isinstance(any_value, InvariantBool)
    assert any_value.value
    assert len(any_value.addresses) == len(invariant_bool_list)


def test_all_helper(invariant_bool_list: list):
    """Test that the all helper returns correct value and keeps all addresses."""
    all_value = F.all(invariant_bool_list)

    assert isinstance(all_value, InvariantBool)
    assert not all_value.value
    assert len(all_value.addresses) == len(invariant_bool_list)


def test_invariant_filter():
    """Test the invariant_filter function."""
    values = [
        InvariantNumber(1, addresses=["addr1"]),
        InvariantNumber(2, addresses=["addr2"]),
        InvariantNumber(3, addresses=["addr3"]),
    ]
    result = F.filter(lambda x: x.value > 1, values)
    assert result == [InvariantNumber(2), InvariantNumber(3)]


def test_invariant_find():
    """Test the invariant_find function."""
    values = [InvariantNumber(1), InvariantNumber(2), InvariantNumber(3)]
    result = F.find(lambda x: x.value > 1, values)
    assert result == InvariantNumber(2)

    result = F.find(lambda x: x.value > 3, values)
    assert result is None

    values = [
        InvariantString("abc"),
        InvariantString("def", addresses=["addr1"]),
        InvariantString("ghi"),
    ]
    result = F.find(lambda x: x.value == "def", values)
    assert result.value == "def"
    assert result.addresses == ["addr1:0-3"]


def test_invariant_min():
    """Test the invariant_min function."""
    values = [InvariantNumber(3), InvariantNumber(1), InvariantNumber(2)]
    result = F.min(values)
    assert result == InvariantNumber(1)


def test_invariant_max():
    """Test the invariant_max function."""
    values = [InvariantNumber(3), InvariantNumber(1), InvariantNumber(2)]
    result = F.max(values)
    assert result == InvariantNumber(3)


def test_match():
    """Test the match helper."""
    values = [
        InvariantString("hi abc", ["m0"]),
        InvariantNumber(1, ["m1"]),
        InvariantString("a", ["m2"]),
        InvariantString("ghi", ["m3"]),
    ]
    result = F.match("a.*", values)
    assert len(result) == 2
    assert result[0].value == "abc" and result[0].addresses == ["m0:3-6"]
    assert result[1].value == "a" and result[1].addresses == ["m2:0-1"]


def test_len_helper_returns_correct_length(invariant_number_list: list):
    """Test that the len function returns the correct length."""
    result = F.len(invariant_number_list)
    assert result == len(invariant_number_list)


def test_len_helper_maintains_addresses(invariant_number_list: list):
    """Test that the len function maintains addresses."""
    result = F.len(invariant_number_list)
    assert result.addresses == [f"{i}" for i in range(len(invariant_number_list))]
    assert len(result.addresses) == len(invariant_number_list)


def test_len_helper_returns_invariant_number(invariant_number_list: list):
    """Test that the len function returns an InvariantNumber object."""
    result = F.len(invariant_number_list)
    assert isinstance(result, InvariantNumber)


def test_len_helper_works_without_addresses():
    """Test that the len function works without addresses."""
    result = F.len([InvariantNumber(1), InvariantNumber(2), InvariantNumber(3)])
    assert result == InvariantNumber(3)
    assert result.addresses == []


def test_check_window_with_builtin_value(invariant_number_list: list):
    """Test that the check_window function works."""
    checks = [4, 2, 4]

    result = F.check_window(checks, invariant_number_list)

    assert result.value
    assert result.addresses == ["3", "4", "5"]


def test_check_window_with_invariant_value(invariant_number_list: list):
    """Test that the check_window function works with InvariantValue objects."""
    checks = [InvariantNumber(4), InvariantNumber(2), InvariantNumber(4)]

    result = F.check_window(checks, invariant_number_list)

    assert result.value
    assert result.addresses == ["3", "4", "5"]


def test_check_window_with_lambda(invariant_number_list: list):
    """Test that the check_window function works with lambda."""
    checks = [lambda x: x % 2 == 0 for _ in range(3)]

    result = F.check_window(checks, invariant_number_list)

    assert result.value
    assert result.addresses == ["2", "3", "4"]


def test_check_window_returns_false(invariant_number_list: list):
    """Test that the check_window function returns False if the order is not correct."""
    checks = [3, 2, 5]

    result = F.check_window(checks, invariant_number_list)

    assert not result.value


@pytest.mark.parametrize(
    "checks, address",
    [
        ([5, 8, 3], ["2"]),
        ([5, 9, 4], ["1"]),
    ],
)
def test_check_window_returns_last_match_address(invariant_number_list: list, checks, address):
    """Test that the check_window function returns the address of the last element that matched when no complete window matched the checks."""
    result = F.check_window(checks, invariant_number_list)

    assert not result.value
    assert result.addresses == address


def test_check_window_returns_first_address_if_no_matches_found(
    invariant_number_list: list,
):
    """Test that the check_window function returns the address of the first element when no (partial) matches are found in any of the windows."""
    checks = [-1, -2, -3]

    result = F.check_window(checks, invariant_number_list)

    assert not result.value
    assert result.addresses == invariant_number_list[0].addresses


def test_check_window_works_over_trace_with_filtering(simple_trace: Trace):
    """Test that the check_window function works over a trace with filtering."""
    checks = [
        lambda m: m["content"] == "Hi, how can I help you?",
        lambda m: m["content"] == "Sure, what do you need help with?",
    ]

    res = F.check_window(checks, simple_trace.messages(role="assistant"))

    assert res.value
    assert res.addresses == ["1", "3"]


def test_check_order_returns_expected(invariant_number_list: list):
    """Test that the check_order function works."""
    # Consecutive numbers
    checks = [4, 2, 4]

    result = F.check_order(checks, invariant_number_list)

    assert result.value
    assert result.addresses == ["3", "4", "5"]

    # Non-consecutive numbers
    checks = [1, 8, 2]

    result = F.check_order(checks, invariant_number_list)

    assert result.value
    assert result.addresses == ["0", "2", "4"]


def test_check_order_returns_false(invariant_number_list: list):
    """Test that the check_order function returns False if the order is not correct."""
    # No match (3 is not in the trace)
    checks = [3, 2, 5]

    result = F.check_order(checks, invariant_number_list)

    assert not result.value
    assert result.addresses == ["0"]

    # No match (2 is never before 5)
    checks = [2, 5, 4]

    result = F.check_order(checks, invariant_number_list)

    assert not result.value
    assert result.addresses == ["4"]


def test_check_order_returns_last_match_address(invariant_number_list: list):
    """Test that the check_order function returns the address of the last element that matched when no complete order matched the checks."""
    checks = [5, 8, 3]

    result = F.check_order(checks, invariant_number_list)

    assert not result.value
    assert result.addresses == ["2"]

    checks = [5, 9, 4]

    result = F.check_order(checks, invariant_number_list)

    assert not result.value
    assert result.addresses == ["1"]


def test_check_order_returns_first_address_if_no_matches_found(
    invariant_number_list: list,
):
    """Test that the check_order function returns the address of the first element when no (partial) matches are found in any of the orders."""
    checks = [-1, -2, -3]

    result = F.check_order(checks, invariant_number_list)

    assert not result.value
    assert result.addresses == ["0"]


def test_check_order_works_with_callable(invariant_number_list: list):
    """Test that the check_order function works with callable."""
    checks = [lambda x: x % 2 == 1, lambda x: x % 2 == 0, lambda x: x % 2 == 0]

    result = F.check_order(checks, invariant_number_list)

    assert result.value
    assert result.addresses == ["0", "2", "3"]


def test_check_returns_first_match_address(invariant_number_list: list):
    """Test that check_order returns the address of the first full match it finds.

    I.e., there are two 4s in the trace, but the first match is at index 3.
    The function should greedily return the first match.
    """
    checks = [1, 5, 4]

    result = F.check_order(checks, invariant_number_list)

    assert result.value
    assert result.addresses == ["0", "1", "3"]


def test_check_handles_duplicate_values(invariant_number_list: list):
    """Test that check_order handles duplicate values correctly."""
    # Should find the first two 4s
    checks = [4, 4]

    result = F.check_order(checks, invariant_number_list)

    assert result.value
    assert result.addresses == ["3", "5"]

    # Should not find multiple 5s
    checks = [5, 5]

    result = F.check_order(checks, invariant_number_list)

    assert not result.value
    assert result.addresses == ["1"]


def test_check_order_handles_empty_checks(invariant_number_list: list):
    """Test that check_order handles empty checks."""
    result = F.check_order([], invariant_number_list)

    assert result.value
    assert result.addresses == []


def test_check_order_handles_check_longer_than_trace(invariant_number_list: list):
    """Test that check_order handles checks that are longer than the trace."""
    checks = [1, 5, 8, 4, 2, 4, 1]
    assert len(checks) > F.len(invariant_number_list), (
        "Invalid test, checks should be longer than the trace."
    )

    result = F.check_order(checks, invariant_number_list)

    # Should return the last matched element
    assert not result.value
    assert result.addresses == ["5"]


def test_check_order_handles_iterable(invariant_number_list: list):
    """Test that check_order handles an iterable of checks."""
    # Should find full match
    checks = [1, 5, 8]

    result = F.check_order(checks, iter(invariant_number_list))

    assert result.value
    assert result.addresses == ["0", "1", "2"]

    # Should find partial match
    checks = [5, 8, 1]

    result = F.check_order(checks, iter(invariant_number_list))

    assert not result.value
    assert result.addresses == ["2"]

    # Should find no match
    checks = [-1, -2, -3]

    result = F.check_order(checks, iter(invariant_number_list))

    assert not result.value
    assert result.addresses == ["0"]


def test_check_window_handles_iterable(invariant_number_list: list):
    """Test that check_window handles an iterable of checks."""
    # Should find full match
    checks = [4, 2, 4]

    result = F.check_window(checks, iter(invariant_number_list))

    assert result.value
    assert result.addresses == ["3", "4", "5"]

    # Should find partial match
    checks = [5, 8, 1]

    result = F.check_window(checks, iter(invariant_number_list))

    assert not result.value
    assert result.addresses == ["2"]

    # Should find no match
    checks = [-1, -2, -3]

    result = F.check_window(checks, iter(invariant_number_list))

    assert not result.value
    assert result.addresses == ["0"]


def test_check_window_handles_empty_values():
    """Test that check_window handles empty values."""
    result = F.check_window([1, 2, 3], [])

    assert not result.value
    assert result.addresses == []
