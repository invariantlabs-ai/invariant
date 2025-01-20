"""Tests for the InvariantNumber class."""

import pytest

from invariant.testing.custom_types.invariant_bool import InvariantBool
from invariant.testing.custom_types.invariant_number import InvariantNumber


def test_invariant_number_initialization():
    """Test initialization of InvariantNumber."""
    num = InvariantNumber(5, ["address1"])
    assert num.value == 5
    assert num.addresses == ["address1"]

    num = InvariantNumber(3.14)
    assert num.value == 3.14
    assert num.addresses == []

    # The value field is read-only.
    with pytest.raises(AttributeError, match="'value' attribute cannot be reassigned"):
        num.value = 5

    with pytest.raises(TypeError, match="value must be an int or float"):
        InvariantNumber("not_a_number")

    with pytest.raises(TypeError, match="addresses must be a list of strings"):
        InvariantNumber(5, [1, 2, 3])


@pytest.mark.parametrize(
    "left, right, operator, expected",
    [
        # Equality cases
        (5, InvariantNumber(5), "==", True),
        (InvariantNumber(5), 5, "==", True),
        (InvariantNumber(5), InvariantNumber(5), "==", True),
        (5, InvariantNumber(3.14), "==", False),
        (5.0, InvariantNumber(5), "==", True),
        (InvariantNumber(3.14), 3.14, "==", True),
        (InvariantNumber(3.14), InvariantNumber(3.14), "==", True),
        # Inequality cases
        (5, InvariantNumber(3), "!=", True),
        (InvariantNumber(5.0), 3.0, "!=", True),
        (InvariantNumber(5), InvariantNumber(3.14), "!=", True),
        (3.14, InvariantNumber(3.14), "!=", False),
        # Greater than cases
        (5, InvariantNumber(3), ">", True),
        (InvariantNumber(5), 3.0, ">", True),
        (InvariantNumber(5.5), InvariantNumber(3.14), ">", True),
        (3, InvariantNumber(5), ">", False),
        # Less than cases
        (3, InvariantNumber(5), "<", True),
        (InvariantNumber(3), 5.0, "<", True),
        (InvariantNumber(3.14), InvariantNumber(5.5), "<", True),
        (5.5, InvariantNumber(3.14), "<", False),
        # Greater than or equal to cases
        (5, InvariantNumber(3), ">=", True),
        (InvariantNumber(5), 5.0, ">=", True),
        (InvariantNumber(5.5), InvariantNumber(3.14), ">=", True),
        (3, InvariantNumber(5), ">=", False),
        # Less than or equal to cases
        (3, InvariantNumber(5), "<=", True),
        (InvariantNumber(3), 5.0, "<=", True),
        (InvariantNumber(3.14), InvariantNumber(3.14), "<=", True),
        (5.5, InvariantNumber(3.14), "<=", False),
    ],
)
def test_invariant_number_comparisons(left, right, operator, expected):
    """Test all comparison operators with InvariantNumber using int and float."""
    result = None
    if operator == "==":
        result = left == right
    elif operator == "!=":
        result = left != right
    elif operator == ">":
        result = left > right
    elif operator == "<":
        result = left < right
    elif operator == ">=":
        result = left >= right
    elif operator == "<=":
        result = left <= right
    else:
        pytest.fail(f"Unknown operator: {operator}")

    assert isinstance(result, InvariantBool)
    assert result.value == expected
    assert isinstance(result.addresses, list)
    if isinstance(left, InvariantNumber):
        assert result.addresses == left.addresses
    elif isinstance(right, InvariantNumber):
        assert result.addresses == right.addresses


def test_invariant_number_str_and_repr():
    """Test string representation of InvariantNumber."""
    num = InvariantNumber(5, ["address1"])
    assert str(num) == "InvariantNumber(value=5, addresses=['address1'])"
    assert repr(num) == "InvariantNumber(value=5, addresses=['address1'])"


def test_mod_operator():
    """Test modulo operator with InvariantNumber."""
    num = InvariantNumber(5, ["address1"]) % InvariantNumber(3, ["address2"])
    assert num.value == 2
    assert num.addresses == ["address1", "address2"]

    num = InvariantNumber(5, ["address1"]) % 3
    assert num.value == 2
    assert num.addresses == ["address1"]

    num = 5 % InvariantNumber(3, ["address2"])
    assert num.value == 2
    assert num.addresses == ["address2"]
