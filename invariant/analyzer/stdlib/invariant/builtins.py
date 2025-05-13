import builtins as py_builtins
import re

from invariant.analyzer.runtime.evaluation import Interpreter
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


def json_loads(s: str) -> dict:
    """
    Parses a JSON string and returns the corresponding Python object.
    """
    import json

    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise JSONDecodeError(f"Invalid JSON string: {s}") from e


def match(pattern: str, s: str) -> bool:
    return re.match(pattern, s) is not None


def find(pattern: str, s: str) -> list[str]:
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
    interpeter = Interpreter.current()
    kwargs["file"] = interpeter.output_stream
    py_builtins.print(*args, **kwargs)
    return True


def tuple(*args, **kwargs):
    """
    Creates a tuple from the given arguments.
    """
    return py_builtins.tuple(*args, **kwargs)


def tool_call(tool_output: ToolOutput, *args, **kwargs) -> ToolCall:
    """
    Gets the tool call object from a tool output.

    Args:
        tool_output: A ToolOutput object.

    Returns:
        The ToolCall object that corresponds to the tool call in the tool output.
    """
    if not isinstance(tool_output, ToolOutput):
        raise ValueError("tool_output argument must be a ToolOutput.")

    return tool_output._tool_call
