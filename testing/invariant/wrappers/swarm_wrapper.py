"""Wrapper for the OpenAI Swarm client."""

from invariant.custom_types.trace import Trace
from invariant.custom_types.trace_factory import TraceFactory
from swarm import Swarm
from swarm.types import Response


class InvariantSwarmResponse(Response):
    """Wrapper around the Swarm Response object."""

    # Represents the full history of messages passed to and from the agent.
    invariant_trace: list[dict]


class SwarmWrapper:
    """Stateless wrapper for the OpenAI Swarm client."""

    def __init__(self, client: Swarm) -> None:
        self.client = client

    @staticmethod
    def to_invariant_trace(invariant_swarm_response: InvariantSwarmResponse) -> Trace:
        """Convert the response to an Invariant Trace."""
        return TraceFactory.from_swarm(invariant_swarm_response.invariant_trace)

    def run(self, *args, **kwargs) -> InvariantSwarmResponse:
        """Call the run method on the Swarm client.

        Sample usage:

        agent = Agent(...)
        swarm_wrapper = SwarmWrapper()

        # First prompt.
        messages = [{"role": "user", "content": "Hello"}]
        response = swarm_wrapper.run(agent=agent, messages=messages, ...)
        # Extend messages with response.messages so that it stores the history of
        # interactions between the user and the agent.
        messages.extend(response.messages)

        # Add a new prompt to the history and pass it to the agent.
        messages.extend([{"role": "user", "content": "What is the capital of France?"}])
        response = swarm_wrapper.run(agent=agent, messages=messages, ...)
        messages.extend(response.messages)
        ...

        Returns:
            InvariantSwarmResponse: The response from the Swarm client, including the
            updated history of messages.
        """
        # Extract 'messages' from kwargs if provided. This represents the full
        # history of messages passed to and from the agent.
        history = kwargs.get("messages")

        # If 'messages' is not in kwargs, it might be in args
        if history is None and len(args) > 0:
            history = args[1]

        response = self.client.run(*args, **kwargs)

        updated_history = history + response.messages
        return InvariantSwarmResponse(
            messages=response.messages,
            agent=response.agent,
            context_variables=response.context_variables,
            invariant_trace=updated_history,
        )
