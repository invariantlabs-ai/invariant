"""Client for interacting with OpenAI."""

import openai
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.parsed_chat_completion import ParsedChatCompletion

from .client import LLMClient


class OpenAIClient(LLMClient):
    """Client for interacting with OpenAI."""

    def __init__(self):
        # Add OPENAI_API_KEY to your environment variables.
        self.client = openai.OpenAI()

    def get_name(self) -> str:
        return "OpenAI"

    def completions_create(self, **request_data) -> ChatCompletion:
        return self.client.chat.completions.create(**request_data)

    def completions_parse(self, **request_data) -> ParsedChatCompletion:
        return self.client.beta.chat.completions.parse(**request_data)
