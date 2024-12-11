"""Abstract base class for LLM clients."""

from abc import ABC, abstractmethod
from typing import Any

try:
    from enum import StrEnum  # Python 3.11+
except ImportError:
    from strenum import StrEnum  # Python < 3.11


class SupportedClients(StrEnum):
    """Enumeration of supported LLM clients."""

    OPENAI = "OpenAI"
    ANTHROPIC = "Anthropic"


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the LLM client."""

    @abstractmethod
    def completions_create(self, **request_data) -> Any:
        """Make a completion request to the LLM."""

    @abstractmethod
    def completions_parse(self, **request_data) -> Any:
        """Make a completion parse request to the LLM."""
