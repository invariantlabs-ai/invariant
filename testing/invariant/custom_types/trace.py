"""Defines an Invariant trace."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Generator, List

from invariant_sdk.client import Client as InvariantClient
from invariant_sdk.types.push_traces import PushTracesResponse
from pydantic import BaseModel

from invariant.custom_types.invariant_dict import InvariantDict, InvariantValue
from invariant.custom_types.matchers import ContainsImage, Matcher
from invariant.utils.utils import ssl_verification_enabled


def iterate_tool_calls(
    messages: list[dict],
) -> Generator[tuple[list[str], dict], None, None]:
    """Generator function to iterate over tool calls in a list of messages.

    Args:
        messages (list[dict]): A list of messages without address information.

    Yields:
        tuple[list[str], dict]: A tuple containing:
            - A list of strings representing the hierarchical address of the tool call
              in the message. For example, `["1.tool_calls.0"]` indicates the first tool
              call in the second message.
            - The tool call data (a dictionary or object representing the tool call).

    Example:
        messages = [
            {"role": "user", "content": "What's the weather?"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "weather_tool",
                            "arguments": {"location": "NYC"}
                        },
                        "id": "call_1",
                        "type": "function"
                    }
                ]
            }
        ]

        for address, tool_call in iterate_tool_calls(messages):
            print(address, tool_call)

        Output:
            ['1.tool_calls.0'] {'function': {'name': 'weather_tool', 'arguments': {'location':
            'NYC'}}, 'id': 'call_1', 'type': 'function'}
    """
    for msg_i, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        tool_calls = msg.get("tool_calls") or []
        for tc_i, tc in enumerate(tool_calls):
            yield [f"{msg_i}.tool_calls.{tc_i}"], tc


def iterate_tool_outputs(
    messages: list[dict],
) -> Generator[tuple[list[str], dict], None, None]:
    """Generator function to iterate over tool outputs in a list of messages.

    Args:
        messages (list[dict]): A list of messages without address information.

    Yields:
        tuple[list[str], dict]: A tuple containing:
            - A list of strings representing the hierarchical address of the tool output
              in the message. For example, `["2"]` indicates the third message in the list.
            - The tool output data (a dictionary or object representing the tool output).
    """
    for msg_i, msg in enumerate(messages):
        if msg.get("role") == "tool":
            yield [f"{msg_i}"], msg


def iterate_messages(
    messages: list[dict],
) -> Generator[tuple[list[str], dict], None, None]:
    """Generator function to iterate over messages in a list of messages.

    Args:
        messages (list[dict]): A list of messages without address information.

    Yields:
        tuple[list[str], dict]: A tuple containing:
            - A list of strings representing the hierarchical address of the message
              in the list. For example, `["1"]` indicates the second message in the list.
            - The message data (a dictionary or object representing the message).
    """
    for msg_i, msg in enumerate(messages):
        yield [f"{msg_i}"], msg


def match_keyword_filter_on_tool_call(
    kwname: str,
    kwvalue: str | int | Callable,
    value: InvariantValue | Any,
    tool_call: dict,
) -> bool:
    # redirect checks on name, arguments and id to the 'function' sub-dictionary
    # this enables checks like tool_calls(name='greet') to work
    if kwname in ["name", "arguments", "id"]:
        value = tool_call["function"].get(kwname)
    return match_keyword_filter(kwname, kwvalue, value, tool_call)


def match_keyword_filter(
    kwname: str,
    kwvalue: str | int | Callable,
    value: InvariantValue | Any,
    message: dict,
) -> bool:
    """Match a keyword filter.

    A keyword filter such as name='value' can be one of the following:
    - a string or integer value to compare against exactly
    - a lambda function to apply to the value to check for more complex conditions

    """
    if isinstance(value, InvariantValue):
        value = value.value

    # compare by value or use a lambda function
    if isinstance(kwvalue, (str, int)):
        return kwvalue == value
    if callable(kwvalue):
        return kwvalue(value)
    raise ValueError(
        f"Cannot filter '{kwname}' with '{kwvalue}' (only str/int comparison or lambda functions are supported)"
    )


def traverse_dot_path(message: dict, path: str) -> Any | None:
    """Traverse a dictionary using a dot-separated path. If argument is not
    found, .function will be added as a prefix to the path to search the
    function fields for tool calls.

    Args:
        message (dict): The message dict to traverse.
        path (str): The dot-separated path to traverse.

    Returns:
        Any: The value at the end of the path, or None if the path does not exist;
             If the function prefix is added, the second return value will be True, otherwise False.
    """
    add_function_prefix = False
    def _inner(d, _path):
        for k in _path.split("."):
            if isinstance(d, str) and isinstance(k, str):
                d = json.loads(d)
            if k not in d:
                return None
            d = d[k]
        return d
    if (res := _inner(message, path)) is None:
        add_function_prefix = True
        return (_inner(message, "function." + path), add_function_prefix)
    return (res, add_function_prefix)


class Trace(BaseModel):
    """Defines an Invariant trace."""

    trace: List[Dict]
    metadata: Dict[str, Any] | None = None

    # Active Manager that is running with this trace as context
    # (e.g. with Trace(...) as trace: ... )
    # If this is already assigned, the trace is currently being used in a context manager already and should not be re-used.
    manager: Any = None

    def __next__(self):
        return next(self._messages())

    def __iter__(self):
        return iter(self._messages())

    def __str__(self):
        return "\n".join(str(msg) for msg in self.trace)

    def _messages(self):
        for i, msg in enumerate(self.trace):
            yield InvariantDict(msg, [str(i)])

    def as_context(self):
        from invariant.manager import Manager

        if self.manager is None:
            self.manager = Manager(self)
        return self.manager

    def run_assertions(self, assertions: list[Callable[Trace, Any]]):
        """Runs a list of assertions on the trace. Assertions are run by providing a list of functions,
        each taking Trace object as a single argument.

        Args:
            assertions: A list of functions taking Trace as a single argument
        """
        for assertion in assertions:
            assertion(self)

    # Functions to check data_types
    @property
    def content_checkers(self) -> Dict[str, Matcher]:
        """Register content checkers for data_types. When implementing a new content checker,
        add the new content checker to the dictionary below.

        Returns:
            Dict[str, Matcher]: The content checkers for the trace.
        """
        __content_checkers__ = {
            "image": ContainsImage(),
        }
        return __content_checkers__

    def _is_data_type(self, message: InvariantDict, data_type: str | None = None) -> bool:
        """Check if a message matches a given data_type using the content_checkers.
        data_type should correspond to the keys in the content_checkers dictionary.
        If data_type is None, the message is considered to match the data_type
        (i.e., no filtering is performed).

        Args:
            message: The message to check.
            data_type: The data_type to check against.

        Returns:
            bool: True if the message matches the data_type, False otherwise.

        Raises:
            ValueError: If the data_type is not supported.
        """
        # If not filtering on data_type
        if data_type is None:
            return True

        # Check message against valid content types
        if data_type in self.content_checkers:
            return message.matches(self.content_checkers[data_type]).value
        else:
            raise ValueError(f"Unsupported data_type: {data_type}")

    def _filter_trace(
        self,
        iterator_func: Callable[
            [list[dict]], Generator[tuple[list[str], dict], None, None]
        ] = iterate_messages,
        match_keyword_function: Callable = match_keyword_filter,
        selector: int | dict | None = None,
        data_type: str | None = None,
        **filterkwargs,
    ) -> list[InvariantDict] | InvariantDict:
        """Filter the trace based on the provided selector, keyword arguments and data_type. Use this
        method as a helper for custom filters such as messages(), tool_calls(), and tool_outputs().

        Args:
            iterator_func: The iterator function to use to iterate over the trace.
                           It should take a list of messages and return a generator
                           that yields tuples of addresses and messages.
            match_keyword_function: The function to use to match keyword filters.
            selector: The selector to use to filter the trace.
            data_type: The data_type to filter on. Uses the content_checkers to check the data_type.
            **filterkwargs: The keyword arguments to use to filter the trace.

        Returns:
            list[InvariantDict] | InvariantDict: The filtered trace.
        """
        # If a single index is provided, return the message at that index
        if isinstance(selector, int):
            for i, (addresses, message) in enumerate(iterator_func(self.trace)):
                if i == selector:
                    return_val = InvariantDict(message, [f"{i}"])
                    return return_val if self._is_data_type(return_val, data_type) else None

        # If a dictionary is provided, filter messages based on the dictionary
        elif isinstance(selector, dict):
            return [
                InvariantDict(message, addresses)
                for addresses, message in iterator_func(self.trace)

                if all(traverse_dot_path(message, kwname)[0] == kwvalue for kwname, kwvalue in selector.items())
                and self._is_data_type(InvariantDict(message, addresses), data_type)
            ]

        # If keyword arguments are provided, filter messages based on the keyword arguments
        elif len(filterkwargs) > 0:
            return [
                InvariantDict(message, addresses)
                for addresses, message in iterator_func(self.trace)
                if all(
                    match_keyword_function(kwname, kwvalue, message.get(kwname), message)
                    for kwname, kwvalue in filterkwargs.items()
                )
                and self._is_data_type(InvariantDict(message, addresses), data_type)
            ]

        # If no selector is provided, return all messages, filtering on data_type.
        return [
            InvariantDict(message, addresses)
            for addresses, message in iterator_func(self.trace)
            if self._is_data_type(InvariantDict(message, addresses), data_type)
        ]

    def messages(
        self,
        selector: int | dict | None = None,
        data_type: str | None = None,
        **filterkwargs,
    ) -> list[InvariantDict] | InvariantDict:
        """Get all messages from the trace that match the provided selector, data_type, and keyword filters.

        Args:
            selector: The selector to use to filter the trace.
            data_type: The data_type to filter on. Uses the content_checkers to check the data_type.
            **filterkwargs: The keyword arguments to use to filter the trace.

        Returns:
            list[InvariantDict] | InvariantDict: The filtered messages.
        """
        if isinstance(selector, int):
            return InvariantDict(self.trace[selector], [str((selector + len(self.trace)) % len(self.trace))])

        return self._filter_trace(iterate_messages, match_keyword_filter, selector, data_type, **filterkwargs)

    def tool_calls(
        self,
        selector: int | dict | None = None,
        data_type: str | None = None,
        **filterkwargs,
    ) -> list[InvariantDict] | InvariantDict:
        """Get all tool calls from the trace that match the provided selector, data_type, and keyword filters.

        Args:
            selector: The selector to use to filter the trace.
            data_type: The data_type to filter on. Uses the content_checkers to check the data_type.
            **filterkwargs: The keyword arguments to use to filter the trace.

        Returns:
            list[InvariantDict] | InvariantDict: The filtered tool calls.
        """
        return self._filter_trace(
            iterate_tool_calls,
            match_keyword_filter_on_tool_call,
            selector,
            data_type,
            **filterkwargs,
        )

    def tool_outputs(
        self,
        selector: int | dict | None = None,
        data_type: str | None = None,
        **filterkwargs,
    ) -> list[InvariantDict] | InvariantDict:
        """Get all tool outputs from the trace that match the provided selector, data_type, and keyword filters.

        Args:
            selector: The selector to use to filter the trace.
            data_type: The data_type to filter on. Uses the content_checkers to check the data_type.
            **filterkwargs: The keyword arguments to use to filter the trace.

        Returns:
            list[InvariantDict] | InvariantDict: The filtered tool outputs.
        """
        return self._filter_trace(
            iterate_tool_outputs,
            match_keyword_filter,
            selector,
            data_type,
            **filterkwargs,
        )

    def tool_pairs(self) -> list[tuple[InvariantDict, InvariantDict]]:
        """Returns the list of tuples of (tool_call, tool_output)."""
        res = []
        for tc_address, tc in iterate_tool_calls(self.trace):
            msg_idx = int(tc_address[0].split(".")[0])
            res.append((msg_idx, InvariantDict(tc, tc_address), None))

        matched_ids = set()
        # First, find all tool outputs that have the same id as a tool call
        for msg_idx, msg in enumerate(self.trace):
            if msg.get("role") != "tool" or "id" not in msg:
                continue
            for i, res_pair in enumerate(res):
                if res_pair[1].get("id") == msg.get("id"):
                    res[i] = (i, res_pair[1], InvariantDict(msg, [f"{msg_idx}"]))
                    matched_ids.add(msg.get("id"))

        res = sorted(res, key=lambda x: x[0])

        # For the remaining tool outputs, assign them to the previous unmatched tool call
        for msg_idx, msg in enumerate(self.trace):
            if msg.get("role") != "tool":
                continue
            if msg.get("id") in matched_ids:
                continue
            for i, res_pair in reversed(list(enumerate(res))):
                tool_call_idx, tool_call, tool_out = res_pair
                if tool_out is None and tool_call_idx < msg_idx:
                    res[i] = (
                        tool_call_idx,
                        tool_call,
                        InvariantDict(msg, [f"{msg_idx}"]),
                    )
                    break

        return [(res_pair[1], res_pair[2]) for res_pair in res if res_pair[2] is not None]

    def to_python(self) -> str:
        """Returns a snippet of Python code construct that can be used
        to recreate the trace in a Python script.

        Returns:
            str: The Python string representing the trace.

        """
        return "Trace(trace=[\n" + ",\n".join("  " + str(msg) for msg in self.trace) + "\n])"

    def push_to_explorer(
        self,
        client: InvariantClient | None = None,
        dataset_name: None | str = None,
    ) -> PushTracesResponse:
        """Pushes the trace to the explorer.

        Args:
            client: The client used to push. If None a standard invariant_sdk client is initialized.
            dataset_name: The name of the dataset to witch the trace would be approved.

        Returns:
            PushTracesResponse: response of push trace request.
        """
        if client is None:
            client = InvariantClient()

        return client.create_request_and_push_trace(
            messages=[self.trace],
            annotations=[],
            metadata=[self.metadata if self.metadata is not None else {}],
            dataset=dataset_name,
            request_kwargs={"verify": ssl_verification_enabled()},
        )
