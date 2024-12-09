"""Describes an invariant number in a test."""

from operator import eq, ge, gt, le, lt, ne
from typing import Union

from invariant.custom_types.invariant_bool import InvariantBool
from invariant.custom_types.invariant_value import InvariantValue


class InvariantNumber(InvariantValue):
    """Describes an invariant number in a test."""

    def __init__(self, value: int | float, addresses: list[str] = None):
        """Initialize the InvariantNumber object."""
        if not isinstance(value, (int, float)):
            raise TypeError(f"value must be an int or float, got {type(value)}")
        if addresses is None:
            addresses = []
        super().__init__(value, addresses)

    def _compare(
        self, other: Union[int, float, "InvariantNumber"], operator
    ) -> "InvariantBool":
        """Helper function to compare with another number."""
        if isinstance(other, InvariantNumber):
            other = other.value
        cmp_result = operator(self.value, other)
        return InvariantBool(cmp_result, self.addresses)

    def __eq__(self, other: Union[int, float, "InvariantNumber"]) -> "InvariantBool":
        """Check if the number is equal to the given number."""
        return self._compare(other, eq)

    def __ne__(self, other: Union[int, float, "InvariantNumber"]) -> "InvariantBool":
        """Check if the number is not equal to the given number."""
        return self._compare(other, ne)

    def __gt__(self, other: Union[int, float, "InvariantNumber"]) -> "InvariantBool":
        """Check if the number is greater than the given number."""
        return self._compare(other, gt)

    def __lt__(self, other: Union[int, float, "InvariantNumber"]) -> "InvariantBool":
        """Check if the number is less than the given number."""
        return self._compare(other, lt)

    def __ge__(self, other: Union[int, float, "InvariantNumber"]) -> "InvariantBool":
        """Check if the number is greater than or equal to the given number."""
        return self._compare(other, ge)

    def __le__(self, other: Union[int, float, "InvariantNumber"]) -> "InvariantBool":
        """Check if the number is less than or equal to the given number."""
        return self._compare(other, le)

    def __add__(self, other):
        """Add two numbers together."""
        if isinstance(other, InvariantNumber):
            return InvariantNumber(
                self.value + other.value, self.addresses + other.addresses
            )
        return InvariantNumber(self.value + other, self.addresses)

    def __radd__(self, other):
        """(reverse) Add two numbers together."""
        return InvariantNumber(other + self.value, self.addresses)

    def __mod__(self, other):
        """Modulo two numbers together."""
        if isinstance(other, InvariantNumber):
            return InvariantNumber(
                self.value % other.value, self.addresses + other.addresses
            )
        return InvariantNumber(self.value % other, self.addresses)

    def __rmod__(self, other):
        """(reverse) Modulo two numbers together."""
        return InvariantNumber(other % self.value, self.addresses)

    def __str__(self) -> str:
        """Return a string representation of the InvariantNumber."""
        return f"InvariantNumber(value={self.value}, addresses={self.addresses})"

    def __repr__(self) -> str:
        """Return a string representation of the InvariantNumber."""
        return str(self)
