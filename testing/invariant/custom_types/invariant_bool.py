"""Describes an invariant boolean in a test."""

import logging
from typing import Union

from invariant.custom_types.invariant_value import InvariantValue
from invariant.utils.logging import ProbabilityFilter

logger = logging.getLogger(__name__)
logger.addFilter(ProbabilityFilter(probability=0.05))
logger.addHandler(logging.StreamHandler())


class InvariantBool(InvariantValue):
    """Describes an invariant bool in a test."""

    def __init__(self, value: bool, addresses: list[str] = None):
        if not isinstance(value, bool):
            raise TypeError(f"value must be a bool, got {type(value)}")
        if addresses is None:
            addresses = []
        super().__init__(value, addresses)

    def __eq__(self, other: Union[bool, "InvariantBool"]) -> "InvariantBool":
        """Check if the boolean is equal to the given boolean."""
        if isinstance(other, InvariantBool):
            return InvariantBool(
                self.value == other.value, self.addresses + other.addresses
            )
        return InvariantBool(self.value == other, self.addresses)

    def __ne__(self, other: Union[bool, "InvariantBool"]) -> "InvariantBool":
        """Check if the boolean is not equal to the given boolean."""
        if isinstance(other, InvariantBool):
            return InvariantBool(
                self.value != other.value, self.addresses + other.addresses
            )
        return InvariantBool(self.value != other, self.addresses)

    def __and__(self, other: Union[bool, "InvariantBool"]) -> "InvariantBool":
        """Evaluate the bitwise AND (&) with the given boolean."""
        if isinstance(other, InvariantBool):
            return InvariantBool(
                self.value and other.value, self.addresses + other.addresses
            )
        return InvariantBool(self.value and other, self.addresses)

    def __rand__(self, other: bool) -> "InvariantBool":
        """Evaluate the bitwise AND (&) with the given boolean (reverse operation)."""
        return InvariantBool(other and self.value, self.addresses)

    def __or__(self, other: Union[bool, "InvariantBool"]) -> "InvariantBool":
        """Evaluate the bitwise OR (|) with the given boolean."""
        if isinstance(other, InvariantBool):
            return InvariantBool(
                self.value or other.value, self.addresses + other.addresses
            )
        return InvariantBool(self.value or other, self.addresses)

    def __ror__(self, other: bool) -> "InvariantBool":
        """Evaluate the bitwise OR (|) with the given boolean (reverse operation)."""
        return InvariantBool(other or self.value, self.addresses)

    def __invert__(self) -> "InvariantBool":
        """Evaluate the bitwise NOT (~) value."""
        return InvariantBool(not self.value, self.addresses)

    def __bool__(self) -> bool:
        """Return the truthiness of the instance."""
        logger.warning(
            "When using `and` and `or`, sometimes due to short-circuiting "
            "the assertions may not be attributed to the given trace correctly. To avoid this,"
            "use the `&` and `|` operators instead."
        )
        return self.value

    def __str__(self) -> str:
        return f"InvariantBool(value={self.value}, addresses={self.addresses})"

    def __repr__(self) -> str:
        return str(self)
