"""Helper functions for searching around collections that contain invariant values."""

# Import built-in functions to avoid shadowing
from builtins import len as builtin_len
from builtins import max as builtin_max
from builtins import min as builtin_min
from collections import deque
from collections.abc import Iterable
from typing import Any, Callable

from invariant.custom_types.invariant_bool import InvariantBool
from invariant.custom_types.invariant_number import InvariantNumber
from invariant.custom_types.invariant_value import InvariantValue
from invariant.custom_types.invariant_string import InvariantString


def map(  # pylint: disable=redefined-builtin
    func: Callable[[InvariantValue], InvariantValue], iterable: Iterable[InvariantValue]
) -> list[InvariantValue]:
    """Apply a function to each element in the iterable and create a new list."""
    return [func(item) for item in iterable]


def reduce_raw(
    func: Callable[[Any, Any], Any],
    initial_value: Any,
    iterable: Iterable[InvariantValue],
) -> Any:
    """Reduce the list instance to a single value using a function and disregarding address information.

    Use this method instead of 'reduce' when the 'func' is not compatible with 'InvariantValue'.
    """
    # Strip address information from values
    values_ = [item.value for item in iterable]

    accumulator = initial_value
    for item in values_:
        accumulator = func(accumulator, item)
    return accumulator


def reduce(
    func: Callable[[InvariantValue, InvariantValue], InvariantValue],
    initial_value: InvariantValue | Any,
    iterable: Iterable[InvariantValue],
) -> InvariantValue:
    """Reduce the list instance to a single value using a function."""
    accumulator = initial_value
    for item in iterable:
        try:
            accumulator = func(accumulator, item)
        except TypeError as e:
            raise TypeError(
                f"Incompatible function: {func} for types '{type(accumulator).__name__}' \
                and '{type(item).__name__}'. "
                "Did you mean to use 'invariant_reduce_raw()'?"
            ) from e
    return accumulator


def count(
    value: InvariantValue | Callable[[InvariantValue | Any], bool] | Any,
    iterable: Iterable[InvariantValue],
) -> InvariantNumber:
    """Count the number of elements in the list that are equal to value or satisfy the condition defined by value.

    Args:
        value: The value to compare against or a function that returns True for elements that
            should be counted.
        iterable: The iterable of InvariantValue objects

    Returns:
        InvariantNumber: The number of elements that match the given value or condition
    """

    def map_func(a):
        if isinstance(value, Callable) and value(a):
            return InvariantNumber(1, a.addresses)
        if a == value:
            return InvariantNumber(1, a.addresses)
        return InvariantNumber(0, a.addresses)

    return sum(map(map_func, iterable))


def frequency(iterable: Iterable[InvariantNumber | InvariantString]) -> dict[int | float | str, InvariantNumber]:
    """Return a dictionary with the frequency of each string in the iterable."""
    freq = {}
    for item in iterable:
        if item.value in freq:
            new_freq = (freq[item.value][0] + 1, freq[item.value][1] + item.addresses)
            freq[item.value] = new_freq
        else:
            freq[item.value] = (1, item.addresses)
    return {k: InvariantNumber(v[0], v[1]) for k, v in freq.items()}


def match(
    pattern: str, iterable: Iterable[InvariantValue], group_id: int | str = 0
) -> list[InvariantValue]:
    """Match the value against the given regex pattern and return the matched group.

    The function calls .match() on each element of the iterable that has .match() function.

    Args:
        pattern: The regex pattern to match against.
        iterable: The iterable of InvariantValue objects to match against.
        group_id: The group ID to return during the match.
    """
    return reduce(
        lambda a, b: a + b,
        [],
        map(
            lambda a: [g] if (g := a.match(pattern, group_id)) else [],
            filter(lambda a: getattr(a, "match", None) and callable(a.match), iterable),
        ),
    )


def any(  # pylint: disable=redefined-builtin
    iterable: Iterable[InvariantValue],
) -> InvariantBool:
    """Return True if any element in the list is True."""
    return reduce(
        lambda element1, element2: element1 | element2,
        InvariantBool(False, []),
        iterable,
    )


def all(  # pylint: disable=redefined-builtin
    iterable: Iterable[InvariantValue],
) -> InvariantBool:
    """Return True if all elements in the list are True."""
    return reduce(
        lambda element1, element2: element1 & element2,
        InvariantBool(True, []),
        iterable,
    )


def filter(  # pylint: disable=redefined-builtin
    predicate: Callable[[InvariantValue], bool], iterable: Iterable[InvariantValue]
) -> list[InvariantValue]:
    """Filter elements of the list based on a predicate."""
    return [item for item in iterable if predicate(item)]


def find(
    predicate: Callable[[InvariantValue], bool],
    iterable: Iterable[InvariantValue],
    default=None,
) -> InvariantValue | Any:
    """Return the first element matching the predicate or None."""
    for item in iterable:
        if predicate(item):
            return item
    return default


def min(  # pylint: disable=redefined-builtin
    iterable: Iterable[InvariantValue],
) -> InvariantValue:
    """Return the minimum value in the list."""
    return builtin_min(iterable, key=lambda x: x.value)


def max(  # pylint: disable=redefined-builtin
    iterable: Iterable[InvariantValue],
) -> InvariantValue:
    """Return the maximum value in the list."""
    return builtin_max(iterable, key=lambda x: x.value)


def len(iterable: Iterable[InvariantValue]) -> InvariantNumber:
    """Return the length of the iterable and the addresses of all elements in the list.

    Args:
        iterable: The iterable of InvariantValue objects.

    Returns:
        InvariantNumber: The length of the iterable with addresses.
    """
    return InvariantNumber(
        builtin_len(iterable), [addr for item in iterable for addr in item.addresses]
    )


def check_order(
    checks: list | list[Callable[[InvariantValue], bool]],
    iterable: Iterable[InvariantValue],
):
    """Check that the elements in the iterable match the checks in order.

    Given a list of checks, this function checks that the elements in the iterable satisfy the checks in order.
    They may have an arbitrary number of messages between them, but the order must be preserved.

    Returns InvariantBool in one of the following ways:
        - InvariantBool(True, all addresses of the elements in the first window that satisfies all checks)
        - InvariantBool(False, last address that matched some part of a check)
        - InvariantBool(False, first address of the iterable otherwise)

    Args:
        checks:   The list of checks to be satisfied. If a check is a function, it should return
                  True if the element satisfies the check. If a check is a value, the element should be
                  equal to the check.

        iterable: An iterable of InvariantValue objects to check against.

    Returns:
        InvariantBool: True if the checks are satisfied in order
    """
    current_check = 0
    check_match_addresses = []

    first_addresses = []

    for message in iterable:
        if not first_addresses:
            first_addresses = message.addresses

        # If all checks are satisfied, break loop
        if current_check >= builtin_len(checks):
            break

        # If the check is a function, call the function with the message
        if isinstance(checks[current_check], Callable):
            if checks[current_check](message):
                current_check += 1
                check_match_addresses.append(message.addresses)

        # If the check is a value, check if the message is equal to the check
        elif message == checks[current_check]:
            current_check += 1
            check_match_addresses.append(message.addresses)

    # If we haven't satisfied all checks, and no matches found, return the address of the first element
    if current_check != builtin_len(checks) and not check_match_addresses:
        return InvariantBool(False, first_addresses)

    # If we haven't satisfied all checks, return the address of the last match
    if current_check != builtin_len(checks) and check_match_addresses:
        return InvariantBool(False, check_match_addresses[-1])

    # Return the (flattened) addresses of the elements that satisfied the checks
    return InvariantBool(
        True, [addr for item in check_match_addresses for addr in item]
    )


def check_window(
    checks: list[InvariantValue] | list[Callable[[InvariantValue], bool]],
    iterable: Iterable[InvariantValue],
) -> InvariantBool:
    """Check that the elements match the checks in a window.

    This function slides the checks over the iterable and checks that the elements match.
    Any window that satisfies the checks will make the function return True in one of the following ways:
        - InvariantBool(True, all addresses of the elements in the first window that satisfies all checks)
        - InvariantBool(False, last address that matched some part of a check)
        - InvariantBool(False, first address of the iterable otherwise)

    Args:
        checks:   The list of checks to be satisfied. If a check is a function, it should return
                  True if the element satisfies the check. If a check is a value, the element should be
                  equal to the check.

        iterable: An iterable of InvariantValue objects to check against.

    Returns:
        InvariantBool: True if the checks are satisfied at least once.
    """

    def _check_if_window_matches(
        window: list[InvariantValue],
    ) -> tuple[bool, list[str]]:
        """Check if a single window matches all the checks.

        Args:
            window: The window of elements to check against the checks.

        Returns:
            tuple[bool, list[str]]: True if the window matches all checks, and the addresses of the elements in the window.
        """
        # Holds the addresses of the last element that matched a check in the window.
        last_match_addresses = []

        for check, element in zip(checks, window):
            if isinstance(check, Callable):
                if not check(element):
                    return False, last_match_addresses

            elif check != element:
                return False, last_match_addresses

            last_match_addresses = element.addresses

        return True, [addr for item in window for addr in item.addresses]

    current_window = deque()
    last_match_addresses = []

    for element in iterable:
        if not last_match_addresses:
            last_match_addresses = element.addresses

        # Add the element to the window
        current_window.append(element)

        # If the window is larger than the checks, pop the leftmost element
        # to keep the window size equal to the checks
        if len(current_window) > builtin_len(checks):
            current_window.popleft()

        # If the window is the same size as the checks, check if it matches
        if len(current_window) == builtin_len(checks):
            if (result := _check_if_window_matches(current_window))[0]:
                return InvariantBool(
                    True,
                    result[1],
                )

            last_match_addresses = result[1] if result[1] else last_match_addresses

    # If no match was found, return the address of the last element that matched
    # some part of the checks
    return InvariantBool(
        False,
        last_match_addresses,
    )
