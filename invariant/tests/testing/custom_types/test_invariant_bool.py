"""Tests for the InvariantBool class."""

import pytest

from invariant.testing.custom_types.invariant_bool import InvariantBool


@pytest.mark.parametrize(
    "bool1, bool2, expected",
    [
        (InvariantBool(True), InvariantBool(True), True),
        (InvariantBool(True), InvariantBool(False), False),
        (InvariantBool(False), InvariantBool(True), False),
        (InvariantBool(False), InvariantBool(False), True),
        (InvariantBool(True), True, True),
        (True, InvariantBool(True), True),
        (False, InvariantBool(True), False),
        (InvariantBool(True), False, False),
        (True, InvariantBool(False), False),
        (InvariantBool(False), True, False),
        (InvariantBool(False), False, True),
        (False, InvariantBool(False), True),
    ],
)
def test_invariant_bool_equality(bool1, bool2, expected):
    """Test the equality of InvariantBool objects."""
    assert (bool1 == bool2).value == expected
    assert (bool1 == bool2) == expected


@pytest.mark.parametrize(
    "bool1, bool2, expected",
    [
        (InvariantBool(True), InvariantBool(True), False),
        (InvariantBool(True), InvariantBool(False), True),
        (InvariantBool(False), InvariantBool(True), True),
        (InvariantBool(False), InvariantBool(False), False),
        (InvariantBool(True), True, False),
        (True, InvariantBool(True), False),
        (False, InvariantBool(True), True),
        (InvariantBool(True), False, True),
        (True, InvariantBool(False), True),
        (InvariantBool(False), True, True),
        (InvariantBool(False), False, False),
        (False, InvariantBool(False), False),
    ],
)
def test_invariant_bool_inequality(bool1, bool2, expected):
    """Test the inequality of InvariantBool objects."""
    assert (bool1 != bool2).value == expected
    assert (bool1 != bool2) == expected


@pytest.mark.parametrize(
    "bool1, bool2, expected",
    [
        (InvariantBool(True), InvariantBool(False), False),
        (InvariantBool(True), InvariantBool(True), True),
        (InvariantBool(False), InvariantBool(True), False),
        (InvariantBool(False), InvariantBool(False), False),
        (InvariantBool(True), True, True),
        (True, InvariantBool(True), True),
        (False, InvariantBool(True), False),
        (InvariantBool(True), False, False),
        (True, InvariantBool(False), False),
        (InvariantBool(False), True, False),
        (InvariantBool(False), False, False),
        (False, InvariantBool(False), False),
    ],
)
def test_invariant_bool_and(bool1, bool2, expected):
    """Test the AND operation of InvariantBool objects."""
    assert (bool1 & bool2).value == expected
    assert (bool1 & bool2) == expected
    assert (bool1 and bool2) == expected


@pytest.mark.parametrize(
    "bool1, bool2, expected",
    [
        (InvariantBool(True), InvariantBool(False), True),
        (InvariantBool(True), InvariantBool(True), True),
        (InvariantBool(False), InvariantBool(True), True),
        (InvariantBool(False), InvariantBool(False), False),
        (InvariantBool(True), True, True),
        (True, InvariantBool(True), True),
        (False, InvariantBool(True), True),
        (InvariantBool(True), False, True),
        (True, InvariantBool(False), True),
        (InvariantBool(False), True, True),
        (InvariantBool(False), False, False),
        (False, InvariantBool(False), False),
    ],
)
def test_invariant_bool_or(bool1, bool2, expected):
    """Test the OR operation of InvariantBool objects."""
    assert (bool1 | bool2).value == expected
    assert (bool1 | bool2) == expected
    assert (bool1 or bool2) == expected


@pytest.mark.parametrize(
    "bool1, expected",
    [
        (InvariantBool(True), False),
        (InvariantBool(False), True),
    ],
)
def test_invariant_bool_not(bool1, expected):
    """Test the NOT operation of InvariantBool objects."""
    assert (~bool1).value == expected
    assert (~bool1) == expected
    assert (not bool1) == expected


@pytest.mark.parametrize(
    "bool1, expected",
    [
        (InvariantBool(True), InvariantBool(True)),
        (InvariantBool(False), InvariantBool(False)),
    ],
)
def test_invariant_bool_identity_and(bool1, expected):
    """Test identity property for AND operation."""
    assert (bool1 & True).value == expected.value
    assert (True & bool1).value == expected.value


@pytest.mark.parametrize(
    "bool1, expected",
    [
        (InvariantBool(True), InvariantBool(True)),
        (InvariantBool(False), InvariantBool(False)),
    ],
)
def test_invariant_bool_identity_or(bool1, expected):
    """Test identity property for OR operation."""
    assert (bool1 | False).value == expected.value
    assert (False | bool1).value == expected.value


@pytest.mark.parametrize(
    "bool1",
    [
        InvariantBool(True),
        InvariantBool(False),
    ],
)
def test_invariant_bool_idempotent(bool1):
    """Test idempotent property for AND and OR operations."""
    assert (bool1 & bool1).value == bool1.value
    assert (bool1 | bool1).value == bool1.value


@pytest.mark.parametrize(
    "bool1, bool2",
    [
        (InvariantBool(True), InvariantBool(False)),
        (InvariantBool(False), InvariantBool(True)),
        (InvariantBool(True), InvariantBool(True)),
        (InvariantBool(False), InvariantBool(False)),
    ],
)
def test_invariant_bool_commutative(bool1, bool2):
    """Test commutative property for AND and OR operations."""
    assert (bool1 & bool2).value == (bool2 & bool1).value
    assert (bool1 | bool2).value == (bool2 | bool1).value


def test_invariant_bool_with_addresses():
    """Test the InvariantBool objects with addresses."""
    bool1 = InvariantBool(True, addresses=["address1"])
    bool2 = InvariantBool(True, addresses=["address1"])
    bool3 = InvariantBool(False, addresses=["address2"])
    assert bool1 == bool2
    assert bool1 != bool3
    assert bool1 == True  # noqa: E712 pylint: disable=singleton-comparison
    assert bool1 != False  # noqa: E712 pylint: disable=singleton-comparison
    assert bool1.addresses == ["address1"]
    assert bool3.addresses == ["address2"]

    # The value field is read-only.
    with pytest.raises(AttributeError, match="'value' attribute cannot be reassigned"):
        bool1.value = False


@pytest.mark.parametrize(
    "invariant_bool, expected",
    [
        (InvariantBool(True), True),
        (InvariantBool(False), False),
    ],
)
def test_invariant_bool_truthiness(invariant_bool, expected):
    """Test the truthiness of InvariantBool objects."""
    assert bool(invariant_bool) == expected


def test_invariant_bool_str():
    """Test the string representation of InvariantBool."""
    bool1 = InvariantBool(True, addresses=["addr1"])
    assert str(bool1) == "InvariantBool(value=True, addresses=['addr1'])"
    assert repr(bool1) == "InvariantBool(value=True, addresses=['addr1'])"

    bool2 = InvariantBool(False, addresses=[])
    assert str(bool2) == "InvariantBool(value=False, addresses=[])"
    assert repr(bool2) == "InvariantBool(value=False, addresses=[])"


@pytest.mark.parametrize("invalid_value", [1, "True", None, [True]])
def test_invariant_bool_invalid_value(invalid_value):
    """Test that invalid values raise a TypeError."""
    with pytest.raises(TypeError, match="value must be a bool"):
        InvariantBool(invalid_value)
