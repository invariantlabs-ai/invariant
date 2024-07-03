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
from invariant.stdlib.invariant.nodes import *

import invariant.language.types as types

def merge(lists):
    if not lists:
        return []
    if len(lists) == 1:
        return lists[0]
    return [item for sublist in lists for item in sublist]


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
            msg_type = derive_type(i)
            if msg_type is None:
                continue

            # if type(i) is not dict: continue
            # flow from all messages to subsequent messages
            self.edges.setdefault(id(i), set()).update(so_far)
            so_far.add(id(i))

            # same for tool calls
            for tc in i.get("tool_calls", []):
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
        if not isinstance(a, dict) or not isinstance(b, dict):
            print("Cannot check flow between non-dict objects", type(a), type(b))
            return False
        if id(a) not in self.edges or id(b) not in self.edges:
            raise KeyError(f"Object with given id not in dataflow graph!")
        return id(a) in self.edges.get(id(b), set())

def is_message(msg_type, obj):
    if not type(obj) is dict:
        return False
    if msg_type == "ToolCall":
        return obj.get("role") == "assistant" and obj.get("tool_calls") is not None and len(obj.get("tool_calls")) > 0
    elif msg_type == "Message":
        return obj.get("role") == "assistant" and obj.get("tool_calls") is None
    elif msg_type == "ToolOutput":
        return obj.get("role") == "tool"
    else:
        return False

class DerivedData(InputProcessor):
    """Creates additional derived data based on some input object.
    
    For instance, this creates links between a ToolOutput and the corresponding 
    preceding ToolCall (either by id or by direct sucessive flow when no id is present).
    
    To access derived properties, use the `get` method.
    """
    def __init__(self):
        self.derived_attributes = {}

    def visit_top_level(self, value_list, name=None):
        tool_calls = {}
        
        for msg in value_list:
            if is_message("ToolCall", msg):
                for tc in msg.get("tool_calls"):
                    tool_calls[tc.get("id", -1)] = tc
                    tool_calls[-1] = msg
            elif is_message("ToolOutput", msg):
                id = msg.get("tool_call_id", -1)
                tool_call = tool_calls.get(id, tool_calls.get(-1, None))
                msg["_tool_call"] = tool_call

    def get(self, obj, key=None):
        all = self.derived_attributes.get(id(obj), {})
        if key is None:
            return all
        return all.get(key)

class InputSchemaValidator(InputProcessor):
    def __init__(self):
        self.valid = False
        self.n_messages = 0
        self.invalid_msg_objects = []

    def visit_top_level(self, value_list, name=None):
        any_valid = False

        for msg in value_list:
            t = derive_type(msg)
            if t is not None:
                self.n_messages += 1
                if t == "Message":
                    # check tool calls
                    tool_calls = msg.get("tool_calls")
                    if tool_calls is not None:
                        for tc in tool_calls:
                            tct = derive_type(tc)
                            if tct == "ToolCall":
                                any_valid = True
                                break
                            else:
                                self.invalid_msg_objects.append(tc)
                any_valid = True
            else:
                self.invalid_msg_objects.append(msg)
        
        self.valid = any_valid or self.valid

    def is_valid(self):
        if self.n_messages == 0:
            return True
        return self.valid and len(self.invalid_msg_objects) == 0
    
    def print_warnings(self):
        if len(self.invalid_msg_objects) > 0:
            warnings.warn("warning: the analysis input contains several objects that could not be recognized by the analyzer as a Message, ToolCall, ToolOutput, etc. Please make sure your input data conforms to the Invariant trace format.", UserWarning)
            for msg in self.invalid_msg_objects:
                warnings.warn(f"warning: unrecognized object: {msg}", UserWarning)

class Selectable:
    def __init__(self, data):
        self.data = data

    def should_ignore(self, data):
        if inspect.isclass(data):
            return True
        if inspect.isfunction(data):
            return True
        return False

    def select(self, selector, data="<root>", index: Optional[int] = None):
        if self.should_ignore(data):
            return []
        type_name = self.type_name(selector)
        if data == "<root>":
            data = self.data

        if type(data) is list:
            if type_name == "list":
                return [(data, index)]
            return merge([self.select(type_name, item, item_index) for item_index, item in enumerate(data)])
        elif type(data) is dict or hasattr(data, "__objectidict__"):
            result = []
            if "type" in data and data["type"] == type_name:
                result.append((data, index))
            elif derive_type(data) == type_name:
                result.append((data, index))
            elif type_name == "dict":
                result.append((data, index))
            for key, value in data.items():
                if key.startswith("_"): continue
                result += self.select(type_name, value, index)
            return result
        elif hasattr(data, "to_dict"):
            result = []
            if derive_type(data) == type_name:
                result.append((data, index))
            for key,value in data.to_dict().items():
                result += self.select(type_name, value, index)
            return result
        elif type(data) is str or type(data) is int or data is None or type(data) is bool: 
            if str(type(data).__name__) == type_name:
                return [(data, index)]
            return []
        elif hasattr(data, "__dict__"):
            result = []
            if data.__class__.__name__ == type_name:
                result.append((data, index))
            for key, value in data.__dict__.items():
                result += self.select(type_name, value, index)
            return result
        elif type(data) is tuple:
            result = []
            for item_index, item in enumerate(data):
                result += self.select(type_name, item, item_index)
            return result
        else:
            print("cannot sub-select type", type(data))
            return []
        
    def type_name(self, selector):
        if type(selector) is types.NamedUnknownType:
            return selector.name
        else:
            return selector
        
def derive_type(dict_value):
    if not hasattr(dict_value, "keys"):
        return None

    if "role" in dict_value.keys() and "content" in dict_value.keys():
        if "tool_call_id" in dict_value.keys():
            return "ToolOutput"
        return "Message"
    elif "type" in dict_value.keys() and "function" in dict_value.keys():
        return "ToolCall"
    else:
        return None

class InputInspector(InputProcessor):
    def __init__(self):
        self.value_lists = []

    def visit_top_level(self, value_list, name=None):
        result = []

        for msg in value_list:
            msg_type = derive_type(msg) or "<unknown>"
            msg_repr = "- " + msg_type + ": " + str(msg)
            if msg_type == "Message":
                for tc in msg.get("tool_calls", []):
                    tct = derive_type(tc) or "<unknown>"
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
    An Input object represents the input to an analyzer call.
    """
    def __init__(self, input_dict, copy=True):
        self.data = deepcopy(input_dict) if copy else input_dict
        # creates derived data from the input (e.g. extra links between different objects)
        self.derived_data = DerivedData.from_input(self.data)
        # check for valid schema
        self.schema_validator = InputSchemaValidator.from_input(self.data)
        self.schema_validator.print_warnings()
        if not self.schema_validator.is_valid(): 
            raise ValueError("the provided input does not conform to the Invariant trace format (see warnings above). Use Input.inspect(obj) to understand how the analyzer interprets your input.")
        # creates a dataflow graph from the input
        self.dataflow = Dataflow.from_input(self.data)
    
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
        
