"""Describes an invariant value in a test."""

from __future__ import annotations

from typing import Any

# pylint: disable=import-outside-toplevel


class InvariantValue:
    """Describes an invariant value in a test."""

    def __init__(self, value: Any, addresses: list[str] = None):
        """Initialize an InvariantValue with a value and a list of addresses."""
        if value is None:
            raise ValueError("InvariantValue cannot be initialized with None value")
        if addresses is not None and not all(
            isinstance(addr, str) for addr in addresses
        ):
            raise TypeError("addresses must be a list of strings")

        self.value = value
        self.addresses = addresses if addresses is not None else []

        if isinstance(self.value, str):
            for i, a in enumerate(self.addresses):
                if ":" not in a:
                    self.addresses[i] = a + ":0-" + str(len(self.value))

    @staticmethod
    def of(value: Any, address: list[str]) -> InvariantValue | "InvariantDict" | None:
        """Create an Invariant type object from a value and a list of addresses."""
        if value is None:
            return None
        if isinstance(value, InvariantValue):
            return value
        from .invariant_bool import InvariantBool
        from .invariant_dict import InvariantDict
        from .invariant_image import InvariantImage
        from .invariant_number import InvariantNumber
        from .invariant_string import InvariantString

        if isinstance(value, dict):
            if not isinstance(address, list):
                raise TypeError(
                    "InvariantValue.of requires a list of addresses for dict values, got "
                    + str(address)
                    + " "
                    + str(type(address))
                )
            return InvariantDict(value, address)
        if isinstance(value, bool):
            return InvariantBool(value, address)
        if isinstance(value, (int, float)):
            return InvariantNumber(value, address)
        if isinstance(value, str) and value.startswith("local_base64_img:"):
            return InvariantImage(value, address)
        if isinstance(value, str):
            return InvariantString(value, address)
        return InvariantValue(value, address)

    def equals(self, value: Any) -> "InvariantBool":  # type: ignore # noqa: F821
        """Check if the value is equal to the given value."""
        from .invariant_bool import InvariantBool

        cmp_result = self.value == value
        # unpack potential InvariantBoolean result
        addresses = [*self.addresses]
        if isinstance(cmp_result, InvariantBool):
            addresses += cmp_result.addresses
            cmp_result = cmp_result.value
        return InvariantBool(cmp_result, addresses)

    def matches(self, matcher: "Matcher") -> "InvariantBool":  # type: ignore # noqa: F821
        """Check if the value matches the given matcher."""
        from .invariant_bool import InvariantBool

        cmp_result = matcher.matches(self.value)
        return InvariantBool(cmp_result, self.addresses)

    def __str__(self):
        """Return a readable string representation of the invariant value."""
        return str(self.value) + " at " + " -> ".join(self.addresses)

    def __repr__(self):
        """Return a string representation of the invariant value."""
        return str(self)

    def __bool__(self) -> bool:
        """Convert the invariant value to a boolean."""
        return bool(self.value)

    def __float__(self) -> float:
        """Convert the invariant value to a float."""
        return float(self.value)

    def __eq__(self, other: Any) -> bool:
        """Check if the invariant value is equal to the given value."""
        return self.value == other
