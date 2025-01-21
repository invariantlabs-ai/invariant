from dataclasses import dataclass
from typing import Union

from pydantic import BaseModel

from invariant.analyzer.runtime.input import Range
from invariant.analyzer.stdlib.invariant.nodes import Event


class AccessDenied:
    pass


ErrorArgument = Union[str, int, float, bool, Event]


class ErrorInformation(BaseModel):
    args: list[ErrorArgument]
    kwargs: dict[str, ErrorArgument]
    ranges: list[Range]

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

    def __repr__(self):
        return str(self)


def PolicyViolation(*args, **kwargs):
    args = list(args)
    ranges = kwargs.get("ranges", [])
    kwargs = {k: v for k, v in kwargs.items() if k != "ranges"}
    return ErrorInformation(args=args, kwargs=kwargs, ranges=ranges)


@dataclass
class UpdateMessage(Exception):
    msg: dict
    content: str
    mode: str = "a"  # p = prepend, a = append, replace = replace


class UpdateMessageHandler:
    def __init__(self, update_message: UpdateMessage):
        self.update_message = update_message

    def apply(self, msg: dict):
        if self.update_message.mode == "a":
            msg["content"] += self.update_message.content
        elif self.update_message.mode == "p":
            msg["content"] = self.update_message.content + msg["content"]
        elif self.update_message.mode == "r":
            msg["content"] = self.update_message.content
        return msg
