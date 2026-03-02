"""
Enables a restricted interface for accessing enabled subset of all
class fields, for objects in invariant policies.

This interface describes the limited object hierarchy the policy is
allowed to interact with, and importantly hides internal fields such
as __dict__ or other unsafe fields that could be used to access the
run-time environment.

Generally, policies and all executed checking functions are also side-effect
free, making runtime manipulation very difficult, however, accessing internal
fields may still be dangerous, as it can leak information about the environment
and the policy itself.

To make an object invariant-accessible, the class must implement the __invariant_attribute__
method, which is called by the invariant_attr function to access an attribute.

The result of the __invariant_attribute__ method must be a safe invariant value itself (primitive, dict, list, tuple, set or another object with __invariant_attribute__ method). If it is not, an exception will be raised.
"""

from types import BuiltinFunctionType, FunctionType, MethodType


def invariant_attr(obj, name: str):
    """
    Access the invariant attribute of an object.

    :param obj: The object to access the invariant attribute from.
    :param name: The name of the invariant attribute to access.

    :return: The value of the invariant attribute.

    :raises AttributeError: If the attribute does not exist on the object.
    :raises ValueError: If the value retrieved is not a safe invariant value (not accessible in the policy context).
    """
    if hasattr(obj, "__invariant_attribute__"):
        result = obj.__invariant_attribute__(name)
        if not is_safe_invariant_value(result):
            raise ValueError(
                f"Policy must not handle values of type {type(result)} ({result}) as returned by .{name} access on {obj.__class__.__name__} objects."
            )
        return result

    if obj is None:
        raise AttributeError(f"Attribute {name} not found on None.")

    if isinstance(obj, list):
        raise AttributeError(
            f"Attribute {name} not found on list. Use list[index] to access elements."
        )

    raise AttributeError(
        f"Attribute {name} not found in {obj.__class__.__name__}. Available attributes are: {', '.join(obj.__dict__.keys())}"
    )


def is_safe_invariant_value(obj):
    # primitive values
    if type(obj) in [str, int, float, bool]:
        return True
    if obj is None:
        return True
    # lists with safe values only
    if isinstance(obj, list):
        return all(is_safe_invariant_value(item) for item in obj)
    # tuples with safe values only
    if isinstance(obj, tuple):
        return all(is_safe_invariant_value(item) for item in obj)
    # sets with safe values only
    if isinstance(obj, set):
        return all(is_safe_invariant_value(item) for item in obj)
    # dictionaries with safe keys and values only
    if isinstance(obj, dict):
        return all(
            is_safe_invariant_value(key) and is_safe_invariant_value(value)
            for key, value in obj.items()
        )
    # objects with well-defined invariant interface
    if hasattr(obj, "__invariant_attribute__"):
        return True
    # function refs are also ok, because they will be checked before calling
    if isinstance(obj, FunctionType):
        return True
    # built-in function refs are also ok, because they will be checked before calling
    if isinstance(obj, BuiltinFunctionType):
        return True
    # bound methods
    if isinstance(obj, MethodType):
        return True

    return False
