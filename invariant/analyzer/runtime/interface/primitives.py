"""
Primitive value wrappers that are used to restrict access to
methods of primitive values.

Generally, we only allow side-effect free, read-only operations
on primitive values. This is to ensure that the evaluation is
deterministic and does not have side effects that could affect
the analysis.


"""

from invariant.analyzer.runtime.runtime_errors import (
    ExcessivePolicyError,
)


class StringValue:
    """
    Wrapper that offers some built-in string methods.
    """

    ALLOWED = ["strip", "lower", "upper", "splitlines", "split", "format", "join"]

    def __init__(self, value: str):
        self.value = value

    def __invariant_attribute__(self, name: str):
        if name not in self.ALLOWED:
            raise ExcessivePolicyError(f"Unavailable attribute {name} for str values.")
        return getattr(self.value, name)


class DictValue:
    """
    Wrapper that offers some built-in dict methods.
    """

    ALLOWED = [
        "keys",
        "values",
        "items",
        "get",
    ]

    def __init__(self, value: dict):
        self.value = value

    def __invariant_attribute__(self, name: str):
        # only support side-effect free, read-only operations
        if name not in self.ALLOWED:
            raise ExcessivePolicyError(f"Unavailable attribute {name} for dict values.")

        return getattr(self.value, name)
