"""Detector for detecting parts of text that match a predicate rule using a language model."""

import json
import logging
from typing import Any, Tuple

from invariant.cache.cache_manager import CacheManager
from invariant.custom_types.addresses import Range
from openai.types.chat.parsed_chat_completion import ParsedChatCompletion
from pydantic import BaseModel

from .clients.anthropic_client import AnthropicClient
from .clients.client import SupportedClients
from .clients.client_factory import ClientFactory
from .clients.open_ai_client import OpenAIClient

OPENAI_LLM_DETECTOR_PROMPT_TEMPLATE = """Your goal is to extract parts of the text the match the
predicate rule. Here is one example:

Predicate rule: 
cities in Switzerland

Text:
1| I arrived to Zurich last week by train from Munich.
2| I am going to visit Geneva next week, and Bern the week after.
3| After Bern, I am going to Paris, France.

Detections:
[("1", "Zurich"), ("2", "Geneva"), ("2", "Bern"), ("3", "Bern")]

Use the following predicate rule to find the detections in the next user message:
{predicate_rule}
"""

ANTHROPIC_LLM_DETECTOR_PROMPT_TEMPLATE = """Your goal is to extract parts of the text the match the
predicate rule. Here is one example:

Predicate rule: 
cities in Switzerland

Text:
1| I arrived to Zurich last week by train from Munich.
2| I am going to visit Geneva next week, and Bern the week after.
3| After Bern, I am going to Paris, France.

Detections:
[("1", "Zurich"), ("2", "Geneva"), ("2", "Bern"), ("3", "Bern")]

You response must be in the following format:
{{
    "detections": [
        {{"line": 1, "substring": "Zurich"}},
        {{"line": 2, "substring": "Geneva"}},
        {{"line": 2, "substring": "Bern"}},
        {{"line": 3, "substring": "Bern"}}
    ]
}}

Use the following predicate rule to find the detections in the next user message:
{predicate_rule}
"""

CACHE_DIRECTORY_LLM_DETECTOR = ".invariant/cache/llm_detector"
CACHE_TIMEOUT = 3600

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DetectionPair(BaseModel):
    """Model for a detection pair."""

    line: int
    substring: str


class Detections(BaseModel):
    """Model for a list of detections."""

    detections: list[DetectionPair]


class Detector:
    """Class to detect using a language model."""

    def _get_prompt(self, predicate_rule: str, client: str) -> str:
        if client == SupportedClients.OPENAI:
            return OPENAI_LLM_DETECTOR_PROMPT_TEMPLATE.format(
                predicate_rule=predicate_rule
            )
        if client == SupportedClients.ANTHROPIC:
            return ANTHROPIC_LLM_DETECTOR_PROMPT_TEMPLATE.format(
                predicate_rule=predicate_rule
            )
        raise ValueError("Invalid client type")

    def __init__(
        self,
        model: str,
        predicate_rule: str,
        client: str = "OpenAI",
    ):
        """
        Args:
            model (str): The language model to use.
            predicate_rule (str): The predicate rule to use for detection. The
            predicate to use for extraction. This is a rule that the LLM uses
            to extract values. For example with a predicate "cities in Switzerland",
            the LLM would extract all cities in Switzerland from the text.
            client (invariant.scorers.llm.clients.client.SupportedClients): The
            client to use for the LLM.
        """
        self.model = model
        self.prompt = self._get_prompt(predicate_rule, client)
        self.client = ClientFactory.get(client)
        self.cache_manager = CacheManager(
            CACHE_DIRECTORY_LLM_DETECTOR, expiry=CACHE_TIMEOUT
        )

    def _insert_lines(self, text: str) -> str:
        return "\n".join(f"{i}| {line}" for i, line in enumerate(text.split("\n"), 1))

    def _to_serializable(self, response):
        """Convert a response object to a JSON-compatible dictionary."""
        return response.model_dump()

    def _from_serializable(self, cached_response):
        """Convert a cached JSON-compatible dictionary back to a response object."""
        return ParsedChatCompletion[Detections].model_validate(cached_response)

    def _generate_cache_key(self, function_name: str, request_data: dict) -> str:
        """Generate a cache key for the request."""
        return self.cache_manager.get_cache_key(
            {
                "function_name": function_name,
                "client": self.client.get_name(),
                "request_data": request_data,
            }
        )

    def _get_detection_request(self, formatted_text: str) -> dict:
        if isinstance(self.client, OpenAIClient):
            return {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": formatted_text},
                ],
                "response_format": Detections,
            }
        if isinstance(self.client, AnthropicClient):
            return {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": formatted_text},
                ],
                "system": self.prompt,
                "max_tokens": 1024,
            }
        raise ValueError("Invalid client type")

    def _parse_detection_response(self, response: Any) -> Detections:
        if isinstance(self.client, OpenAIClient):
            return response.choices[0].message.parsed
        if isinstance(self.client, AnthropicClient):
            return Detections.model_validate(json.loads(response.content[0].text))
        raise ValueError("Invalid client type")

    def _make_completions_parse_request(
        self, request_data: dict, use_cached_result: bool
    ):
        """Make a request to the language model."""
        if not use_cached_result:
            return self.client.completions_parse(**request_data)

        cache_key = self._generate_cache_key("completions_parse", request_data)
        response = self.cache_manager.get(cache_key)
        if response:
            logger.info("Using cached response for request.")
            if isinstance(self.client, OpenAIClient):
                return self._from_serializable(response)
            return response

        logger.info("Cache miss. Making request to LLM Client.")
        # Make the actual request
        response = self.client.completions_parse(**request_data)

        if isinstance(self.client, OpenAIClient):
            # Store the response in a serializable format
            serializable_response = self._to_serializable(response)
            self.cache_manager.set(cache_key, serializable_response)
        else:
            self.cache_manager.set(cache_key, response)

        return response

    def detect(
        self, text: str, use_cached_result: bool = True
    ) -> list[Tuple[str, Range]]:
        """Detect parts of the text that match the predicate rule.

        Args:
            text (str): The text to detect on.
            use_cached_result (bool): Whether to use a cached result if available.
        """
        formatted_text = self._insert_lines(text)
        response = self._make_completions_parse_request(
            {
                **self._get_detection_request(formatted_text),
            },
            use_cached_result,
        )
        detections = self._parse_detection_response(response)
        return [
            (
                det.substring,
                Range.from_line(text, det.line - 1, exact_match=det.substring),
            )
            for det in detections.detections
        ]
