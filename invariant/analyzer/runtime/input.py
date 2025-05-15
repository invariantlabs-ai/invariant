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
from typing import Callable, List, Optional

from pydantic import BaseModel
from rich.pretty import pprint as rich_print

import invariant.analyzer.language.types as types
from invariant.analyzer.runtime.nodes import (
    Contents,
    Event,
    Image,
    Message,
    TextChunk,
    Tool,
    ToolCall,
    ToolOutput,
    ToolParameter,
)
from invariant.analyzer.runtime.runtime_errors import InvariantInputValidationError

from .range import Range


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

    def __init__(self, edges=None, parents=None):
        self.edges = edges or {}
        self.parents = parents or {}

    def visit_top_level(self, value_list, name=None):
        so_far = set()
        previous = None

        # iterate over messages in chat
        for i in value_list:
            # if type(i) is not dict: continue
            # flow from all messages to subsequent messages
            self.edges.setdefault(id(i), set()).update(so_far)
            so_far.add(id(i))

            # Update parents
            self.parents[id(i)] = previous
            previous = id(i)

            # same for tool calls
            if type(i) is Message and i.tool_calls is not None:
                for tc in i.tool_calls:
                    self.edges.setdefault(id(tc), set()).update(so_far)
                    so_far.add(id(tc))

                    # Update parents
                    self.parents[id(tc)] = previous
                    previous = id(tc)

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

    def is_parent(self, a, b):
        """Returns whether a is an immediate predecessor of b in the dataflow graph.

        Args:
            a: The source object (must be the same (id(...)) object, as when creating the graph).
            b: The target object (must be the same (id(...)) object, as when creating the graph).

        Returns:
            True if a is an immediate predecessor of b, False otherwise.
        """
        if id(a) not in self.parents or id(b) not in self.parents:
            raise KeyError("Object with given id not in dataflow graph!")
        return self.parents[id(b)] == id(a)


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
        elif type(data) is Tool:
            return self.merge(
                [
                    self.select(type_name, data.inputSchema),
                ]
            )
        elif type(data) is Contents:
            return self.merge([self.select(type_name, item) for item in data])
        elif type(data) is Image:
            return self.merge([self.select(type_name, data.image_url)])
        elif type(data) is TextChunk:
            return self.merge([self.select(type_name, data.text)])
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
        # when traversing a .content field, we recursively traverse each
        # content chunk, e.g. [{"type": "text", "text": <content>}, ...]
        elif isinstance(object, Contents):
            # treat 'Contents' like a list of chunks
            for i in range(len(object.root)):
                self.visit(object.root[i], path + [i])
        elif isinstance(object, BaseModel):
            # get pydantic model fields
            fields = object.__class__.model_fields
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

        for event in input:
            try:
                if not isinstance(event, dict):
                    parsed_data.append(event)
                    continue
                if "role" in event:
                    if event["role"] != "tool":
                        # if arguments are given as string convert them into dict using json.loads(...)
                        for call in event.get("tool_calls") or []:
                            if type(call["function"]["arguments"]) is str:
                                call["function"]["arguments"] = json.loads(
                                    call["function"]["arguments"]
                                )

                        # note: enable the following to ensure all .content fields will be lists of [{"type": "text", "text": ...}, ...]
                        # # convert .content str to [{"type": "text": <content>}]
                        # if type(event.get("content")) is str:
                        #     event["content"] = [{"type": "text", "text": event["content"]}]

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
                elif "tools" in event:

                    def parse_tool_param(
                        name: str, schema: dict, required_keys: Optional[List[str]] = None
                    ) -> ToolParameter:
                        param_type = schema.get("type", "string")
                        description = schema.get("description", "")

                        # Only object-level schemas have required fields as a list
                        if required_keys is None:
                            required_keys = schema.get("required", [])

                        aliases = {
                            "integer": "number",
                            "int": "number",
                            "float": "number",
                            "bool": "boolean",
                            "str": "string",
                            "dict": "object",
                            "list": "array",
                        }
                        if param_type in aliases:
                            param_type = aliases[param_type]

                        if param_type == "object":
                            properties = {}
                            for key, subschema in schema.get("properties", {}).items():
                                properties[key] = parse_tool_param(
                                    name=key if " arguments" in name else f"{name}.{key}",
                                    schema=subschema,
                                    required_keys=schema.get("required", []),
                                )
                            return ToolParameter(
                                name=name,
                                type="object",
                                description=description,
                                required=name in required_keys,
                                properties=properties,
                                additionalProperties=schema.get("additionalProperties"),
                            )
                        elif param_type == "array":
                            return ToolParameter(
                                name=name,
                                type="array",
                                description=description,
                                required=name in required_keys,
                                items=parse_tool_param(name=f"{name} item", schema=schema["items"]),
                            )
                        elif param_type in ["object", "array", "string", "number", "boolean"]:
                            return ToolParameter(
                                name=name,
                                type=param_type,
                                description=description,
                                required=name in required_keys,
                                enum=schema.get("enum"),
                            )
                        else:
                            raise InvariantInputValidationError(
                                f"Unsupported schema type: {param_type} for parameter {name}. Supported types are: object, array, string, number, boolean."
                            )

                    for tool in event["tools"]:
                        name = tool["name"]
                        # Parse the input schema properties
                        properties = []
                        for key, subschema in tool["inputSchema"].get("properties", {}).items():
                            properties.append(
                                parse_tool_param(
                                    name=key,
                                    schema=subschema,
                                    required_keys=tool["inputSchema"].get("required", []),
                                )
                            )

                        tool_obj = Tool(
                            name=name,
                            description=tool["description"],
                            inputSchema=properties,
                        )
                        parsed_data.append(tool_obj)
                else:
                    raise InvariantInputValidationError(
                        "Input should be a list of one of (Message, ToolCall, ToolOutput, Tool). See the documentation for the schema requirements. Instead, got: "
                        + str(event)
                    )
            except Exception as e:
                warnings.warn(f"Could not parse event in the trace: {event}!", stacklevel=1)
                raise e

        for trace_idx, event in enumerate(parsed_data):
            event.metadata["trace_idx"] = trace_idx

            if (
                hasattr(event, "tool_calls")
                and event.tool_calls
                and isinstance(event.tool_calls, list)
            ):
                for tool_call in event.tool_calls:
                    tool_call.metadata["trace_idx"] = trace_idx

        return parsed_data

    def has_flow(self, a, b):
        return self.dataflow.has_flow(a, b)

    def is_parent(self, a, b):
        return self.dataflow.is_parent(a, b)

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
