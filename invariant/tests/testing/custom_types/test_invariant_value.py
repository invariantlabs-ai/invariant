"""Tests for the InvariantValue class."""

import pytest

from invariant.testing.custom_types.invariant_bool import InvariantBool
from invariant.testing.custom_types.invariant_dict import InvariantDict
from invariant.testing.custom_types.invariant_number import InvariantNumber
from invariant.testing.custom_types.invariant_string import InvariantString
from invariant.testing.custom_types.invariant_value import InvariantValue
from invariant.testing.custom_types.matchers import LambdaMatcher


def test_invariant_value_initialization():
    """Test initialization of InvariantValue."""
    invariant_value = InvariantValue("test", ["address1"])
    assert invariant_value.value == "test"
    assert invariant_value.addresses == ["address1:0-4"]

    invariant_value = InvariantValue(123)
    assert invariant_value.value == 123
    assert invariant_value.addresses == []

    # The value field is read-only.
    with pytest.raises(AttributeError, match="'value' attribute cannot be reassigned"):
        invariant_value.value = "new value"

    with pytest.raises(TypeError, match="addresses must be a list of strings"):
        InvariantValue("test", ["address1", 123])

    with pytest.raises(ValueError, match="cannot be initialized with None value"):
        InvariantValue(None, ["address1", 123])


def test_invariant_value_of():
    """Test the static method 'of' for creating InvariantValue objects."""
    value = InvariantValue.of("test", ["address1"])
    assert isinstance(value, InvariantString)
    assert value.value == "test"
    assert value.addresses == ["address1:0-4"]

    value = InvariantValue.of(123, ["address1"])
    assert isinstance(value, InvariantNumber)
    assert value.value == 123
    assert value.addresses == ["address1"]

    value = InvariantValue.of(0, ["address1"])
    assert isinstance(value, InvariantNumber)
    assert value.value == 0
    assert value.addresses == ["address1"]

    value = InvariantValue.of(123.45, ["address1"])
    assert isinstance(value, InvariantNumber)
    assert value.value == 123.45
    assert value.addresses == ["address1"]

    value = InvariantValue.of(True, ["address1"])
    assert isinstance(value, InvariantBool)
    assert value.value is True
    assert value.addresses == ["address1"]

    value = InvariantValue.of({"key": "value"}, ["address1"])
    assert isinstance(value, InvariantDict)
    assert value.value == {"key": "value"}
    assert value.addresses == ["address1"]

    with pytest.raises(TypeError):
        InvariantValue.of({"key": "value"}, "address1")

    value = InvariantValue.of(InvariantValue("test", ["address1"]), ["address1"])
    assert isinstance(value, InvariantValue)
    assert value.value == "test"
    assert value.addresses == ["address1:0-4"]

    class SomeClass:
        """Some demo class"""

    some_instance = SomeClass()
    value = InvariantValue.of(some_instance, ["address1"])
    assert isinstance(value, InvariantValue)
    assert value.value == some_instance
    assert value.addresses == ["address1"]

    assert InvariantValue.of(None, ["address1"]) is None


def test_invariant_value_equals():
    """Test the 'equals' method of InvariantValue."""
    value1 = InvariantValue("test", ["address1"])
    value2 = InvariantValue("test", ["address1"])
    value3 = InvariantValue("different", ["address1"])

    result = value1.equals(value2.value)
    assert isinstance(result, InvariantBool)
    assert result.value is True

    result = value1.equals(value3.value)
    assert isinstance(result, InvariantBool)
    assert result.value is False

    result = value1.equals("test")
    assert isinstance(result, InvariantBool)
    assert result.value is True

    result = value1.equals("different")
    assert isinstance(result, InvariantBool)
    assert result.value is False


def test_invariant_value_str():
    """Test the __str__ method of InvariantValue."""
    value = InvariantValue("test", ["address1"])
    assert str(value) == "test at address1:0-4"

    value = InvariantValue(123, ["address1"])
    assert str(value) == "123 at address1"

    value = InvariantValue(True, ["address1"])
    assert str(value) == "True at address1"


def test_invariant_value_repr():
    """Test the __repr__ method of InvariantValue."""
    value = InvariantValue("test", ["address1"])
    assert repr(value) == "test at address1:0-4"

    value = InvariantValue(123, ["address1"])
    assert repr(value) == "123 at address1"

    value = InvariantValue(True, ["address1"])
    assert repr(value) == "True at address1"


def test_invariant_value_bool():
    """Test the __bool__ method of InvariantValue."""
    assert bool(InvariantValue(1)) is True  # Non-zero number
    assert bool(InvariantValue(0)) is False  # Zero
    assert bool(InvariantValue("non-empty")) is True  # Non-empty string
    assert bool(InvariantValue("")) is False  # Empty string
    assert bool(InvariantValue([])) is False  # Empty list
    assert bool(InvariantValue([1, 2, 3])) is True  # Non-empty list


def test_invariant_value_float():
    """Test the __float__ method of InvariantValue."""
    assert float(InvariantValue(42)) == 42.0  # Integer to float
    assert float(InvariantValue(42.5)) == 42.5  # Float remains float
    assert float(InvariantValue("42.5")) == 42.5  # String representing a float
    with pytest.raises(ValueError):  # Invalid string for float conversion
        float(InvariantValue("invalid"))
    with pytest.raises(TypeError):  # Non-convertible type
        float(InvariantValue([]))


def test_invariant_value_eq():
    """Test the __eq__ method of InvariantValue."""
    # Equality with primitives
    assert InvariantValue(42) == 42
    assert InvariantValue("test") == "test"
    assert InvariantValue(True) == True  # noqa: E712
    assert InvariantValue(3.14) == 3.14

    # Equality with complex types
    assert InvariantValue([1, 2, 3]) == [1, 2, 3]
    assert InvariantValue({"key": "value"}) == {"key": "value"}

    # Non-equal cases
    assert InvariantValue(42) != 43
    assert InvariantValue("test") != "not test"
    assert InvariantValue([1, 2, 3]) != [1, 2]
    assert InvariantValue({"key": "value"}) != {"key": "different_value"}


def test_invariant_value_matches():
    """Test the matches function in InvariantValue."""
    # Define a lambda matcher that checks for even numbers
    matcher = LambdaMatcher(lambda x: x % 2 == 0)

    # Test with a matching value
    value = InvariantValue(4, ["address1"])
    result = value.matches(matcher)
    assert isinstance(result, InvariantBool)
    assert result.value is True
    assert result.addresses == ["address1"]

    # Test with a non-matching value
    value = InvariantValue(5, ["address2"])
    result = value.matches(matcher)
    assert isinstance(result, InvariantBool)
    assert result.value is False
    assert result.addresses == ["address2"]

    # Test with a string matcher
    string_matcher = LambdaMatcher(lambda x: "test" in x)
    value = InvariantValue("this is a test", ["address3"])
    result = value.matches(string_matcher)
    assert isinstance(result, InvariantBool)
    assert result.value is True
    assert result.addresses == ["address3:0-14"]

    # Test with a non-matching string value
    value = InvariantValue("no match here", ["address4"])
    result = value.matches(string_matcher)
    assert isinstance(result, InvariantBool)
    assert result.value is False
    assert result.addresses == ["address4:0-13"]

    # Test with an invalid matcher (not a Matcher instance)
    with pytest.raises(AttributeError):
        value.matches("not_a_matcher")
