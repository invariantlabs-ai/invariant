from invariant.stdlib.invariant.nodes import *
from invariant.runtime.input import Input
from invariant.stdlib.invariant.errors import *
from invariant.stdlib.invariant.message import *
from invariant.runtime.utils.base import DetectorResult
from invariant.runtime.functions import nocache
import builtins as py_builtins

# Utilities

def any(iterable):
    if isinstance(iterable, list) and len(iterable) > 0:
        if isinstance(iterable[0], DetectorResult):
            return True
    return py_builtins.any(iterable)


# String operations

def match(pattern: str, s: str) -> bool:
    import re
    return re.match(pattern, s) is not None

def len(s: str) -> int:
    return py_builtins.len(s)

# Arithmetic

def min(*args, **kwargs):
    return py_builtins.min(*args, **kwargs)

def max(*args, **kwargs):
    return py_builtins.max(*args, **kwargs)

def sum(*args, **kwargs):
    return py_builtins.sum(*args, **kwargs)

# Utilities

@nocache
def print(*args, **kwargs):
    """
    Prints the given arguments just like with Python's built-in print function.

    Note that `print(...)` must be used only on the top-level of a rule body. With respect
    to boolean semantics, `print(...)` does not have any effect on the rule evaluation 
    (e.g. neither True nor False), and rather is filtered out during the evaluation process.
    """
    py_builtins.print(*args, **kwargs)
    return True
