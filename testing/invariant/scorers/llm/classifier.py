"""Module for the LLM Classifier class."""

import json
import logging
from enum import Enum
from typing import Any

from invariant.cache.cache_manager import CacheManager

from .clients.anthropic_client import AnthropicClient
from .clients.client_factory import ClientFactory
from .clients.open_ai_client import OpenAIClient

PROMPT_TEMPLATE = """Your goal is to classify the text provided by the user
using the following classification rule.
{prompt}

Call the function `option_selector` with the best of the following options as the argument: {options}
"""

PROMPT_TEMPLATE_VISION = """Your goal is to classify the image provided by the user
using the following classification rule.
{prompt}

Call the function `option_selector` with the best of the following options as the argument: {options}
"""
OPTION_SELECTOR_TOOL_ARG = "classification_result"
CACHE_DIRECTORY_LLM_CLASSIFIER = ".invariant/cache/llm_classifier"
CACHE_TIMEOUT = 3600
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "option_selector",
            "description": "Selects the best option from the list of options",
            "parameters": {
                "type": "object",
                "properties": {
                    OPTION_SELECTOR_TOOL_ARG: {
                        "type": "string",
                    },
                },
            },
        },
    }
]
ANTHROPIC_TOOLS = [
    {
        "name": "option_selector",
        "description": "Selects the best option from the list of options",
        "input_schema": {
            "type": "object",
            "properties": {
                OPTION_SELECTOR_TOOL_ARG: {
                    "type": "string",
                }
            },
            "required": [OPTION_SELECTOR_TOOL_ARG],
        },
    }
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Classifier:
    """Class to classify using a language model."""

    def __init__(
        self,
        model: str,
        prompt: str,
        options: list[str],
        vision: bool = False,
        client: str = "OpenAI",
    ):
        """
        Args:
            model (str): The language model to use.
            prompt (str): The prompt to use for the classification.
            options (list[str]): The options to choose from when classifying.
            vision (bool): Whether to classify images instead of text.
            client (invariant.scorers.llm.clients.client.SupportedClients): The
            client to use for the LLM.
        """
        self.model = model
        self.prompt = (
            PROMPT_TEMPLATE_VISION.format(prompt=prompt, options=",".join(options))
            if vision
            else PROMPT_TEMPLATE.format(prompt=prompt, options=",".join(options))
        )
        self.client = ClientFactory.get(client)
        self.cache_manager = CacheManager(
            CACHE_DIRECTORY_LLM_CLASSIFIER, expiry=CACHE_TIMEOUT
        )

    def _create_classification_request(self, text: str) -> dict:
        if isinstance(self.client, OpenAIClient):
            return {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": text},
                ],
                "tools": OPENAI_TOOLS,
                "tool_choice": "required",
            }
        if isinstance(self.client, AnthropicClient):
            return {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": text},
                ],
                "system": self.prompt,
                "max_tokens": 1024,
                "tools": ANTHROPIC_TOOLS,
            }
        raise ValueError("Invalid client type")

    def _parse_classification_response(self, response: Any, default: str) -> str:
        if isinstance(self.client, OpenAIClient):
            return json.loads(
                response.choices[0].message.tool_calls[0].function.arguments
            ).get(OPTION_SELECTOR_TOOL_ARG, default)
        if isinstance(self.client, AnthropicClient):
            for block in response.content:
                if block.type == "tool_use" and block.name == "option_selector":
                    return block.input.get(OPTION_SELECTOR_TOOL_ARG)
            return default
        raise ValueError("Invalid client type")

    def _create_vision_classification_request(
        self, base64_image: str, image_type: str
    ) -> dict:
        if isinstance(self.client, OpenAIClient):
            return {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            }
                        ],
                    },
                ],
                "tools": OPENAI_TOOLS,
                "tool_choice": "required",
            }
        if isinstance(self.client, AnthropicClient):
            return {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_type,
                                    "data": f"{base64_image}",
                                },
                            },
                        ],
                    },
                ],
                "system": self.prompt,
                "max_tokens": 1024,
                "tools": ANTHROPIC_TOOLS,
            }
        raise ValueError("Invalid client type")

    def _generate_cache_key(self, function_name: str, request_data: dict) -> str:
        """Generate a cache key for the request."""
        return self.cache_manager.get_cache_key(
            {
                "function_name": function_name,
                "client": self.client.get_name(),
                "request_data": request_data,
            }
        )

    def _make_completions_create_request(
        self, request_data: dict, use_cached_result: bool
    ) -> Any:
        """Make a request to the language model."""
        if not use_cached_result:
            return self.client.completions_create(**request_data)

        cache_key = self._generate_cache_key("completions_create", request_data)
        response = self.cache_manager.get(cache_key)
        if response:
            logger.info("Using cached response for request.")
            return response

        logger.info("Cache miss. Making request to LLM Client.")
        # Make the actual request
        response = self.client.completions_create(**request_data)

        # Store the response in the cache with an expiry
        self.cache_manager.set(cache_key, response)

        return response

    def classify_vision(
        self,
        base64_image: str,
        image_type: str = "image/jpeg",
        use_cached_result: bool = True,
        default: str = "none",
    ) -> str:
        """Classify an image using the language model.

        Args:
            base64_image (str): The base64-encoded image to classify.
            image_type (str): The MIME type of the image.
            use_cached_result (bool): Whether to use a cached result if available.
            default (str): The default classification if the model fails to classify.
        """
        response = self._make_completions_create_request(
            {
                **self._create_vision_classification_request(base64_image, image_type),
            },
            use_cached_result,
        )
        return self._parse_classification_response(response, default)

    def classify(
        self, text: str, use_cached_result: bool = True, default: str = "none"
    ) -> str:
        """Classify a text using the language model.

        Args:
            text (str): The text to classify.
            use_cached_result (bool): Whether to use a cached result if available.
            default (str): The default classification if the model fails to classify.
        """
        response = self._make_completions_create_request(
            {
                **self._create_classification_request(text),
            },
            use_cached_result,
        )
        return self._parse_classification_response(response, default)
