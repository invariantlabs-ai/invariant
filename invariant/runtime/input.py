"""
Models input data passed to the Invariant Agent Analyzer.

Creates dataflow graphs and derived data from the input data.
"""
import inspect
import warnings
import textwrap
import termcolor
from copy import deepcopy
from typing import Optional
from invariant.stdlib.invariant.nodes import Message, ToolCall, ToolOutput, Event

import invariant.language.types as types


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
            raise KeyError(f"Object with given id not in dataflow graph!")
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

    def select(self, selector, data="<root>", index: Optional[int] = None):
        if self.should_ignore(data):
            return []
        type_name = self.type_name(selector)
        if data == "<root>":
            data = self.data

        if type(data).__name__ == type_name:
            return [(data, index)]

        if type(data) is Message:
            return self.merge([
                self.select(type_name, data.content, index),
                self.select(type_name, data.role, index),
                self.select(type_name, data.tool_calls, index),
                self.select(type_name, data.data, index)
            ])
        elif type(data) is ToolCall:
            return self.merge([
                self.select(type_name, data.id, index),
                self.select(type_name, data.type, index),
                self.select(type_name, data.function, index),
                self.select(type_name, data.data, index)
            ])
        elif type(data) is ToolOutput:
            return self.merge([
                self.select(type_name, data.role, index),
                self.select(type_name, data.content, index),
                self.select(type_name, data.tool_call_id, index),
                self.select(type_name, data.data, index)
            ])
        elif type(data) is list:
            return self.merge([self.select(type_name, item, item_index) for item_index, item in enumerate(data)])
        elif type(data) is dict:
            return self.merge([self.select(type_name, value, index) for value in data.values()])
        elif type(data) is tuple:
            return self.merge([self.select(type_name, item, item_index) for item_index, item in enumerate(data)])
        else:
            # print("cannot sub-select type", type(data))
            return []
        
    def type_name(self, selector):
        if type(selector) is types.NamedUnknownType:
            return selector.name
        else:
            return selector

class InputInspector(InputProcessor):
    """Input processor that prints a human-readable representation of the input data."""
    def __init__(self):
        self.value_lists = []

    def visit_top_level(self, value_list, name=None):
        result = []

        for msg in value_list:
            msg_type = type(msg).__name__ or "<unknown>"
            msg_repr = "- " + msg_type + ": " + str(msg)
            if msg_type == "Message":
                tool_calls = msg.tool_calls or []
                for tc in tool_calls:
                    tct = type(tc).__name__ or "<unknown>"
                    msg_repr += "\n  - " + tct + ": " + str(tc)
            result += [msg_repr]

        self.value_lists.append((name, "\n".join(result)))
    
    def __str__(self):
        result = ""
        for name, l in self.value_lists:
            if name is None:
                result += "<root>:\n"
            else:
                result += f"{name}:\n"
            
            result += textwrap.indent(l, "  ")
        
        return result

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
            if not isinstance(event, dict):
                parsed_data.append(event)
                continue
            if "role" in event:
                if event["role"] != "tool":
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
                raise ValueError("Could not parse event in the trace as any of the event types (Message, ToolCall, ToolOutput): " + str(event))
        return parsed_data
    
    @staticmethod
    def inspect(obj):
        """
        Prints a string representation of the input object, 
        as the analyzer would see it.
        """
        inspector = InputInspector.from_input(obj)
        return str(inspector)

    def has_flow(self, a, b):
        return self.dataflow.has_flow(a, b)

    def __str__(self):
        return f"<Input {self.data}>"
    
    def __repr__(self):
        return str(self)
    
    def validate(self):
        """
        Validates whether the provided input conforms to a schema that
        can be handled by the analyzer.
        """
        
