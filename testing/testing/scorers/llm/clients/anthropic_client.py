"""Client for interacting with Anthropic Claude."""

from typing import Any

from .client import LLMClient


class AnthropicClient(LLMClient):
    """Client for interacting with Anthropic Claude."""

    def __init__(self):
        from anthropic import Anthropic  # pylint: disable=import-outside-toplevel

        # Add ANTHROPIC_API_KEY to your environment variables.
        self.client = Anthropic()

    def get_name(self) -> str:
        return "Anthropic"

    def completions_create(self, **request_data) -> Any:
        return self.client.messages.create(**request_data)

    def completions_parse(self, **request_data) -> Any:
        return self.completions_create(**request_data)
