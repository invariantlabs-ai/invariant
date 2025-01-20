import builtins as py_builtins
import re

from invariant.analyzer.runtime.input import Input  # noqa
from invariant.analyzer.stdlib.invariant.errors import *
from invariant.analyzer.stdlib.invariant.message import *
from invariant.analyzer.stdlib.invariant.nodes import *

# Utilities


def any(iterable):
    return py_builtins.any(iterable)


def empty(iterable) -> bool:
    """Returns True if iterable is empty, False otherwise."""
    return len(iterable) == 0


# String operations


def match(pattern: str, s: str) -> bool:
    return re.match(pattern, s) is not None


def find(pattern: str, s: str) -> list[str]:
    from invariant.analyzer.runtime.evaluation import Interpreter

    interpreter = Interpreter.current()

    res = []
    for match in re.finditer(pattern, s):
        interpreter.mark(s, match.start(), match.end())
        res.append(match.group())
    return res


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


def print(*args, **kwargs):
    """
    Prints the given arguments just like with Python's built-in print function.

    Note that `print(...)` must be used only on the top-level of a rule body. With respect
    to boolean semantics, `print(...)` does not have any effect on the rule evaluation
    (e.g. neither True nor False), and rather is filtered out during the evaluation process.
    """
    py_builtins.print(*args, **kwargs)
    return True
