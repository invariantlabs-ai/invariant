"""Factory for creating LLM clients."""

from .anthropic_client import AnthropicClient
from .client import LLMClient, SupportedClients
from .open_ai_client import OpenAIClient


class ClientFactory:
    """Factory for creating LLM clients."""

    @staticmethod
    def get(client_name: str, client_kwargs: dict) -> LLMClient:
        """Get an LLM client by name."""
        if client_name == SupportedClients.OPENAI:
            return OpenAIClient(client_kwargs)
        if client_name == SupportedClients.ANTHROPIC:
            return AnthropicClient()
        raise ValueError(f"Invalid client name: {client_name}")
