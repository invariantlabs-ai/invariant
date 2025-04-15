import textwrap
from dataclasses import dataclass
from typing import Optional, Union

from pydantic import BaseModel, Field

from invariant.analyzer.language.ast import PolicyError
from invariant.analyzer.runtime.nodes import Contents, Message, ToolCall, ToolOutput
from invariant.analyzer.runtime.range import Range
from invariant.analyzer.stdlib.invariant.nodes import Event


class AccessDenied:
    pass


ErrorArgument = Union[str, int, float, bool, Event, Message, ToolOutput, ToolCall, Contents]


class ErrorInformation(BaseModel):
    args: list[ErrorArgument]
    kwargs: dict[str, ErrorArgument]
    ranges: list[Range]

    key: Optional[str] = Field(
        default=None,
        description="An optional key to identify this error across runs. This key is computed on the underlying variable assignment and thus should be stable across runs.",
    )

    def __str__(self):
        kvs = ", ".join(
            [
                f"{k}={v}" if k != "ranges" else f"ranges=[<{len(self.ranges)} ranges>]"
                for k, v in self.kwargs.items()
            ]
        )
        if len(kvs) > 0:
            kvs = ", " + kvs
        return f"{type(self).__name__}({' '.join([str(a) for a in self.args])}{kvs})"

    def to_dict(self):
        args = self.args

        # for each value, make sure it is a valid 'ErrorArgument', otherwise stringify it
        for i in range(len(args)):
            if isinstance(args[i], BaseModel):
                args[i] = args[i].model_dump()
            elif not isinstance(args[i], (str, int, float, bool)):
                args[i] = str(args[i])

        kwargs = self.kwargs

        # for each value, make sure it is a valid 'ErrorArgument', otherwise stringify it
        for k, v in kwargs.items():
            if isinstance(v, BaseModel):
                kwargs[k] = v.model_dump()
            elif not isinstance(v, (str, int, float, bool)):
                kwargs[k] = str(v)

        return {
            "key": self.key if self.key else None,
            "args": [a.model_dump() if type(a) is BaseModel else a for a in args],
            "kwargs": {k: v.model_dump() if type(v) is BaseModel else v for k, v in kwargs.items()},
            "ranges": [r.to_address() for r in self.ranges],
        }

    @classmethod
    def from_dict(cls, error: dict):
        """
        Creates a local 'Range' object for the given error address (e.g. messages.1.content:10-20).
        """
        args = error.pop("args", [])
        kwargs = error.pop("kwargs", {})
        translated_ranges = [Range.from_address(r) for r in error["ranges"]]
        key = error.get("key", None)

        return cls(args=args, kwargs=kwargs, ranges=translated_ranges, key=key)

    def __hash__(self):
        return hash(
            (
                tuple(self.args),
                tuple(sorted(self.kwargs.items())),
                tuple(sorted([str(r) for r in self.ranges])),
            )
        )

    def __repr__(self):
        return str(self)


def Violation(*args, **kwargs):
    args = list(args)
    ranges = kwargs.get("ranges", [])
    kwargs = {k: v for k, v in kwargs.items() if k != "ranges"}

    return ErrorInformation(args=args, kwargs=kwargs, ranges=ranges)


def PolicyViolation(*args, **kwargs):
    """
    Deprecated alias for Violation.
    """
    return Violation(*args, **kwargs)


@dataclass
class UpdateMessage(Exception):
    msg: dict
    content: str
    mode: str = "a"  # p = prepend, a = append, replace = replace


class UpdateMessageHandler:
    def __init__(self, update_message: UpdateMessage):
        self.update_message = update_message

    async def apply(self, msg: dict):
        if self.update_message.mode == "a":
            msg["content"] += self.update_message.content
        elif self.update_message.mode == "p":
            msg["content"] = self.update_message.content + msg["content"]
        elif self.update_message.mode == "r":
            msg["content"] = self.update_message.content
        return msg


@dataclass
class UnhandledError(Exception):
    errors: list[PolicyError]

    def __str__(self):
        errors_noun = "errors" if len(self.errors) > 1 else "error"
        errors_list = "\n".join(
            [" - " + type(error).__name__ + ": " + str(error) for error in self.errors]
        )
        return f"A policy analysis resulted in {len(self.errors)} unhandled {errors_noun}:\n{errors_list}.\n"


class AnalysisResult(BaseModel):
    """
    Result of applying a policy to an application state.

    Includes all unresolved errors, as well as resolved (handled) errors
    with corresponding handler calls (run them to actually resolve
    them in the application state).
    """

    errors: list[ErrorInformation]

    def __str__(self):
        width = 120

        errors_str = "\n".join(
            [
                f"{textwrap.indent(textwrap.fill(str(error), width=width), ' ' * 4)}"
                for error in self.errors
            ]
        )
        error_line = "  errors=[]" if len(self.errors) == 0 else f"  errors=[\n{errors_str}\n  ]"

        return f"AnalysisResult(\n{error_line}\n)"

    def to_dict(self):
        """Converts the analysis result to a dictionary."""
        return {"errors": [error.to_dict() for error in self.errors]}

    def __repr__(self):
        return self.__str__()


@dataclass
class PolicyLoadingError(Exception):
    """
    This exception is raised when a policy could not be loaded due to errors in
    the policy source (parsing, scoping, typing, validation, etc.).
    """

    msg: str
    errors: list[PolicyError]

    def __str__(self):
        return self.msg
