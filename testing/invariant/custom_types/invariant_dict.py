"""InvariantDict class definition for a dict type"""

from typing import Any

from invariant.custom_types.invariant_bool import InvariantBool
from invariant.custom_types.invariant_value import InvariantValue


class InvariantDict:
    """Invariant implementation of a dict type"""

    def __init__(self, value: dict, address: list):
        """Initialize an InvariantDict with a value and a list of addresses."""
        if not isinstance(value, dict):
            raise TypeError("value must be a dictionary, got " + str(type(value)))
        if not isinstance(address, list):
            raise TypeError("addresses must be a list, got " + str(type(address)))
        self.value = value
        self.addresses = address

    def _wrap_value(self, key: str, value: Any) -> InvariantValue | None:
        if value is None:
            return None
        return InvariantValue.of(value, [f"{a}.{key}" for a in self.addresses])

    def __getitem__(self, key) -> InvariantValue | None:
        """Allows for dictionary-like access to the value using square brackets."""
        if key not in self.value:
            raise KeyError(f"Key {key} not found in {self.value}")

        return self._wrap_value(key, self.value[key])

    def get(self, key, default: Any = None) -> InvariantValue | Any:
        """Get the value of the key or return the default value if the key is not found."""
        value = self.value.get(key)
        if value is None:
            return default

        return self._wrap_value(key, value)

    def __str__(self) -> str:
        return "InvariantDict" + str(self.value) + " at " + str(self.addresses)

    def matches(self, matcher: "Matcher") -> "InvariantBool":  # type: ignore # noqa: F821
        """Check if the value matches the given matcher."""

        cmp_result = matcher.matches(self.value)
        return InvariantBool(cmp_result, self.addresses)

    def __repr__(self) -> str:
        return str(self)
    
    def __eq__(self, other: "InvariantDict") -> bool:
        """Check if the InvariantDict value is equal to the given value."""
        if not isinstance(other, InvariantDict):
            raise TypeError(f"Cannot compare InvariantDict with {type(other)}")
        return self.value == other.value
