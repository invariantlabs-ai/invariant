"""Tests for the code module."""

from invariant.testing.scorers.code import is_valid_json, is_valid_python


def test_is_valid_json():
    """Test the is_valid_json function."""
    assert is_valid_json("""{"key": "value"}""")[0]
    assert not is_valid_json("not json")[0]


def test_is_valid_python():
    """Test the is_valid_python function."""
    assert is_valid_python("print('hello')")[0]
    assert not is_valid_python("2 = b")[0]
