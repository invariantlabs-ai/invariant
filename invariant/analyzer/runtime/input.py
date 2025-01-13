"""
Models input data passed to the Invariant Agent Analyzer.

Creates dataflow graphs and derived data from the input data.
"""

import copy
import inspect
import json
import re
import warnings
from collections.abc import ItemsView, KeysView, ValuesView
from copy import deepcopy
from typing import Callable, Optional

from pydantic import BaseModel
from rich.pretty import pprint as rich_print

import invariant.analyzer.language.types as types
from invariant.analyzer.stdlib.invariant.nodes import Event, Message, ToolCall, ToolOutput


class InputProcessor:
    """
    Simple visitor to traverse input data and process it in some way
    (to build a dataflow graph or to change the input data in some way).
    """

    def process(self, input_dict):
        # determine all top-level lists in the input
        top_level_lists = []
        if type(input_dict) is list:
            top_level_lists.append(input_dict)
        elif type(input_dict) is dict:
            for k, v in input_dict.items():
                if type(v) is list:
                    top_level_lists.append(v)

        for l in top_level_lists:
            self.visit_top_level(l)

    def visit_top_level(self, value_list, name=None):
        pass

    @classmethod
    def from_input(cls, input_dict):
        processor = cls()
        processor.process(input_dict)
        return processor


class Dataflow(InputProcessor):
    """Stores the dataflow within a given input.

    For now, this constructs a sequential graph per top-level list in the input, or
    for the input itself, if the input is a list.

    For instance `{ "messages": [1,2,3], "llm_calls": [4,5,6] }` would create a graph with
    the following edges `1 -> 2, 2 -> 3, 1 -> 3` and `4 -> 5, 5 -> 6, 4 -> 6`.

    Important: All objects are identified by their id() in the graph.
    """

    def __init__(self, edges=None):
        self.edges = edges or {}

    def visit_top_level(self, value_list, name=None):
        so_far = set()
        # iterate over messages in chat
        for i in value_list:
            # if type(i) is not dict: continue
            # flow from all messages to subsequent messages
            self.edges.setdefault(id(i), set()).update(so_far)
            so_far.add(id(i))

            # same for tool calls
            if type(i) is Message and i.tool_calls is not None:
                for tc in i.tool_calls:
                    self.edges.setdefault(id(tc), set()).update(so_far)
                    so_far.add(id(tc))

    def has_flow(self, a, b):
        """Returns whether there is a flow from a to b in the dataflow graph.

        Args:
            a: The source object (must be the same (id(...)) object, as when creating the graph).
            b: The target object (must be the same (id(...)) object, as when creating the graph).

        Returns:
            True if there is a flow from a to b, False otherwise.
        """
        if id(a) not in self.edges or id(b) not in self.edges:
            raise KeyError("Object with given id not in dataflow graph!")
        return id(a) in self.edges.get(id(b), set())


class Selectable:
    def __init__(self, data):
        self.data = data

    def should_ignore(self, data):
        if inspect.isclass(data):
            return True
        if inspect.isfunction(data):
            return True
        return False

    def merge(self, lists):
        if not lists:
            return []
        if len(lists) == 1:
            return lists[0]
        return [item for sublist in lists for item in sublist]

    def select(self, selector, data="<root>"):
        if self.should_ignore(data):
            return []
        type_name = self.type_name(selector)
        # allow to select the Input object itself
        if type_name == "Input":
            return [self]
        # allow to select the root data object
        if data == "<root>":
            data = self.data
        if self.should_ignore(data):
            return []
        if isinstance(data, (KeysView, ValuesView, ItemsView)):
            return self.select(selector, list(data))
        type_name = self.type_name(selector)

        if type(data).__name__ == type_name:
            return [data]

        if type(data) is Message:
            return self.merge(
                [
                    self.select(type_name, data.content),
                    self.select(type_name, data.role),
                    self.select(type_name, data.tool_calls),
                ]
            )
        elif type(data) is ToolCall:
            return self.merge(
                [
                    self.select(type_name, data.id),
                    self.select(type_name, data.type),
                    self.select(type_name, data.function),
                ]
            )
        elif type(data) is ToolOutput:
            return self.merge(
                [
                    self.select(type_name, data.role),
                    self.select(type_name, data.content),
                    self.select(type_name, data.tool_call_id),
                ]
            )
        elif type(data) is list:
            return self.merge([self.select(type_name, item) for item in data])
        elif type(data) is dict:
            return self.merge([self.select(type_name, value) for value in data.values()])
        elif type(data) is tuple:
            return self.merge([self.select(type_name, item) for item in data])
        else:
            # print("cannot sub-select type", type(data))
            return []

    def type_name(self, selector):
        if type(selector) is types.NamedUnknownType:
            return selector.name
        else:
            return selector


def inputcopy(opj):
    # recursively copy, dict, list and tuple, and delegate to deepcopy for leaf objects
    if type(opj) is dict:
        result = {k: inputcopy(v) for k, v in opj.items()}
        result["__origin__"] = opj
        return result
    elif type(opj) is list:
        return [inputcopy(v) for v in opj]
    elif type(opj) is tuple:
        return tuple([inputcopy(v) for v in opj])
    else:
        return deepcopy(opj)


class Range(BaseModel):
    """
    Represents a range in the input object that is relevant for
    the currently evaluated expression.

    A range can be an entire object (start and end are None) or a
    substring (start and end are integers, and object_id refers to
    the object that the range is part of).
    """

    object_id: str
    start: Optional[int]
    end: Optional[int]

    # json path to this range in the input object (not always directly available)
    # Use Input.locate to generate the JSON paths
    json_path: Optional[str] = None

    @classmethod
    def from_object(cls, obj, start=None, end=None):
        if type(obj) is dict and "__origin__" in obj:
            obj = obj["__origin__"]
        return cls(object_id=str(id(obj)), start=start, end=end)

    def match(self, obj):
        return str(id(obj)) == self.object_id


class InputVisitor:
    def __init__(self, data):
        self.data = data
        self.visited = set()

    def visit(self, object=None, path=None):
        # root call defaults
        if object is None:
            object = self.data
        if path is None:
            path = []

        # prevent infinite recursion
        if id(object) in self.visited:
            return
        self.visited.add(id(object))

        if type(object) is dict:
            for k in object:
                self.visit(object[k], path + [k])
        elif type(object) is list:
            for i, v in enumerate(object):
                self.visit(v, path + [i])
        elif isinstance(object, BaseModel):
            # get pydantic model fields
            fields = object.model_fields
            for field in fields:
                self.visit(getattr(object, field), path + [field])
        else:
            return  # nop


class RangeLocator(InputVisitor):
    def __init__(self, ranges, data):
        super().__init__(data)

        self.ranges_by_object_id = {}
        for r in ranges:
            self.ranges_by_object_id.setdefault(r.object_id, []).append(r)
        self.results = []

    def visit(self, object=None, path=None):
        if object is None:
            object = self.data
        if path is None:
            path = []

        if str(id(object)) in self.ranges_by_object_id:
            for r in self.ranges_by_object_id[str(id(object))]:
                rpath = ".".join(map(str, path))
                if r.start is not None and r.end is not None:
                    rpath += ":" + str(r.start) + "-" + str(r.end)
                self.results.append((r, rpath))

        super().visit(object, path)


def mask_json_paths(input: list[dict], json_paths: list[str], mask_fn: Callable):
    def find_next(rpath: str) -> list[str]:
        return [
            json_path[len(rpath) + 1 :] for json_path in json_paths if json_path.startswith(rpath)
        ]

    def visit(object=None, path=None):
        if path is None:
            path = []

        rpath = ".".join(map(str, path))
        next_paths = find_next(rpath)
        if len(next_paths) == 0:
            return copy.deepcopy(object)

        if type(object) is str:
            new_object = copy.deepcopy(object)
            for next_path in next_paths:
                match = re.match(r"^(\d+)-(\d+)$", next_path)
                if match:
                    start, end = map(int, match.groups())
                    new_object = (
                        new_object[:start] + mask_fn(new_object[start:end]) + new_object[end:]
                    )
            return new_object
        elif type(object) is dict:
            return {k: visit(object[k], path + [k]) for k in object}
        elif type(object) is list:
            return [visit(v, path + [i]) for i, v in enumerate(object)]
        else:
            raise ValueError(f"Cannot mask object of type {type(object)}")

    return visit(input, [])


class Input(Selectable):
    """
    An Input object that can be analyzed by the Invariant Analyzer.

    Attributes:
        data: List of events observed in the input where each event is one of Message, ToolCall or ToolOutput.
        dataflow: Dataflow graph of the events in the input.
    """

    data: list[Event]
    dataflow: Dataflow

    def __init__(self, input: list[dict]):
        self.data = self.parse_input(input)
        # creates a dataflow graph from the input
        self.dataflow = Dataflow.from_input(self.data)

    def locate(self, ranges: list[Range], object=None, path=None, results=None):
        locator = RangeLocator(ranges, self.data)
        locator.visit(object, path)
        # return new ranges, where the json path is set
        ranges_with_paths = locator.results
        return [
            Range(object_id=r.object_id, start=r.start, end=r.end, json_path=path)
            for r, path in ranges_with_paths
        ]

    def to_json(self):
        return json.dumps([event.model_dump_json() for event in self.data])

    def parse_input(self, input: list[dict]) -> list[Event]:
        """Parses input data given as list of dictionaries and transforms it into list of Event objects (Message, ToolCall or ToolOutput).

        Args:
            input: List of dictionaries representing the raw input data (for example, as received from the user).
        """
        input = deepcopy(input)
        parsed_data = []
        tool_calls = {}
        last_call_id = None

        for message_idx, event in enumerate(input):
            try:
                if not isinstance(event, dict):
                    parsed_data.append(event)
                    continue
                if "role" in event:
                    if event["role"] != "tool":
                        # If arguments are given as string convert them into dict using json.loads(...)
                        for call in event.get("tool_calls", []):
                            if type(call["function"]["arguments"]) == str:
                                call["function"]["arguments"] = json.loads(
                                    call["function"]["arguments"]
                                )
                        msg = Message(**event)
                        parsed_data.append(msg)
                        if msg.tool_calls is not None:
                            for call in msg.tool_calls:
                                last_call_id = call.id
                                tool_calls[call.id] = call
                    else:
                        if "tool_call_id" not in event:
                            event["tool_call_id"] = last_call_id
                        out = ToolOutput(**event)
                        if out.tool_call_id in tool_calls:
                            out._tool_call = tool_calls[out.tool_call_id]
                        parsed_data.append(out)
                elif "type" in event:
                    call = ToolCall(**event)
                    last_call_id = call.id
                    tool_calls[call.id] = call
                    parsed_data.append(call)
                else:
                    raise ValueError(
                        "Could not parse event in the trace as any of the event types (Message, ToolCall, ToolOutput): "
                        + str(event)
                    )
            except Exception as e:
                warnings.warn(f"Could not parse event in the trace: {event}!")
                raise e

        for trace_idx, event in enumerate(parsed_data):
            event.metadata["trace_idx"] = trace_idx
        return parsed_data

    def has_flow(self, a, b):
        return self.dataflow.has_flow(a, b)

    def print(self, expand_all=False):
        rich_print("<Input>")
        for event in self.data:
            rich_print(event, expand_all=expand_all)

    def __str__(self):
        return f"<Input {self.data}>"

    def __repr__(self):
        return str(self)

    def validate(self):
        """
        Validates whether the provided input conforms to a schema that
        can be handled by the analyzer.
        """
