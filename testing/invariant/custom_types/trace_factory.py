"""Defines a factory for creating traces of custom types."""

import copy
from typing import Any

from invariant.utils.explorer import from_explorer

from .trace import Trace


class TraceFactory:
    """A factory for creating traces of custom types."""

    @staticmethod
    def from_swarm(history: list[dict]) -> Trace:
        """Creates a Trace instance from the history of messages exchanged with the Swarm client.

        Args:
            history (list[dict]): The history of messages exchanged with the Swarm client.

        Returns:
            Trace: A Trace object with all the messages combined.
        """
        return TraceFactory.from_openai(history)

    @staticmethod
    def from_langgraph(invocation_response: dict[str, Any] | Any) -> Trace:
        """Converts a Langgraph invocation response to a Trace object.

        Sample usage:

        app = workflow.compile(...)
        invocation_response = app.invoke(
            {"messages": [HumanMessage(content="what is the weather in sf")]}
        )
        trace = TraceFactory.from_langgraph(invocation_response)

        """
        from langchain_community.adapters.openai import (
            convert_message_to_dict,
        )  # pylint: disable=import-outside-toplevel

        messages = []
        for message in invocation_response["messages"]:
            messages.append(convert_message_to_dict(message))
        return Trace(trace=messages)

    @staticmethod
    def from_explorer(
        identifier_or_id: str,
        index: int | None = None,
        explorer_endpoint: str = "https://explorer.invariantlabs.ai",
    ) -> Trace:
        """Loads a public trace from the Explorer (https://explorer.invariantlabs.ai).

        The identifier_or_id can be either a trace ID or a <username>/<dataset> pair, in which case
        the index of the trace to load must be provided.

        Args:
            identifier_or_id: The trace ID or <username>/<dataset> pair.
            index: The index of the trace to load from the dataset.

        Returns:
            Trace: A Trace object with the loaded trace.

        :return: A Trace object with the loaded trace.
        """
        messages, metadata = from_explorer(identifier_or_id, index, explorer_endpoint)
        return Trace(trace=messages, metadata=metadata)

    @staticmethod
    def from_openai(messages: list[dict]) -> Trace:
        """
        Creates a Trace instance from the history messages exchanged with the openai client.

        Args:
            messages (list[dict]): The history messages exchanged with the openai client.

        Returns:
            Trace: A Trace object with all the messages combined.
        """

        assert isinstance(messages, list)
        assert all(isinstance(msg, dict) for msg in messages)
        trace_messages = copy.deepcopy(messages)
        return Trace(trace=trace_messages)
