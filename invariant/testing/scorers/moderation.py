"""A module for detecting text content that violates moderation guidelines."""

from typing import Optional, Tuple

from invariant.testing.custom_types.addresses import Range

from .utils.base import BaseDetector

MODERATION_CATEGORIES = {
    "OpenAI": {
        "harassment": "harassment",
        "hate": "hate",
        "self-harm": "self_harm",
        "sexual": "sexual",
        "violence": "violence",
        "sexual/minors": "sexual/minors",
        "hate/threatening": "hate/threatening",
        "violence/graphic": "violence/graphic",
    }
}

MODERATION_CATEGORIES_INV = {
    provider: {v: k for k, v in provider_mapping.items()}
    for provider, provider_mapping in MODERATION_CATEGORIES.items()
}


class ModerationAnalyzer(BaseDetector):
    """A class for analyzing and detecting text content that violates moderation guidelines.

    The ModerationAnalyzer class leverages different moderation models (e.g., OpenAI)
    to detect text content that falls into predefined categories such as harassment,
    hate speech, self-harm, and graphic violence. The moderation categories and their mappings
    are configurable for different providers.

    Example:
        analyzer = ModerationAnalyzer()
        results = analyzer.detect_all(
            text="Some potentially harmful text.",
            model="OpenAI",
            default_threshold=0.7,
        )
        print(results)  # Outputs: [('harassment', Range(start=0, end=25))]

    """

    def __init__(self):
        pass

    def _initialize_client(self, model: str):
        """Initialize and return the client for the specified model."""
        if model == "OpenAI":
            import openai  # pylint: disable=import-outside-toplevel

            return openai.Client()
        raise ValueError(f"Model {model} not supported.")

    def _split_text(
        self, text: str, split: Optional[str], max_length: int = 2000
    ) -> list[str]:
        """Split text into chunks by delimiter and maximum length."""
        if split:
            text_splits = [
                split + chunk if i > 0 else chunk
                for i, chunk in enumerate(text.split(split))
            ]
        else:
            text_splits = [text]

        chunks = []
        for chunk in text_splits:
            if len(chunk) > max_length:
                chunks.extend(
                    [
                        chunk[i : i + max_length]
                        for i in range(0, len(chunk), max_length)
                    ]
                )
            else:
                chunks.append(chunk)

        return chunks

    def _moderate_with_openai(self, client, text: str):
        """Moderate text using OpenAI's moderation model."""
        # NOTE: OpenAI suggests: for higher accuracy, try splitting long pieces of text into
        # smaller chunks each less than 2,000 characters.
        moderated = client.moderations.create(input=text)
        scores = moderated.results[0].category_scores.to_dict()
        scores = {
            MODERATION_CATEGORIES["OpenAI"][category]: score
            for category, score in scores.items()
            if category in MODERATION_CATEGORIES["OpenAI"]
        }
        return scores

    def detect_all(  # pylint: disable=arguments-differ
        self,
        text: str,
        split: Optional[str] = "\n",
        model: str = "OpenAI",
        default_threshold: float = 0.5,
        category_thresholds: Optional[dict[str, float]] = None,
    ) -> list[Tuple[str, Range]]:
        """Provides tools to detect text content that may violate moderation guidelines.

        Args:
            text: The text to analyze.
            split: The delimiter to split the text into chunks.
            model: The model to use for moderation detection.
            default_threshold: The threshold for the model score above which text is considered
                to be moderated.
            category_thresholds: A dictionary of category-specific thresholds.

        Returns:
            A list of (category, range) objects, each representing a substring that should be
            moderated.

        """
        client = self._initialize_client(model)

        # split by a delimiter
        # TODO: Invariant Language doesn't support split=\n, so let's always split for now
        text_chunks = self._split_text(text, split)

        if len(text) != sum(len(chunk) for chunk in text_chunks):
            raise RuntimeError("Mismatch in text splitting logic.")

        result = []
        pos = 0

        for chunk in text_chunks:
            scores = (
                self._moderate_with_openai(client, chunk) if model == "OpenAI" else {}
            )
            flagged = None
            for category in MODERATION_CATEGORIES_INV[model]:
                if scores[category] > default_threshold:
                    flagged = category
                if (
                    category_thresholds
                    and category in category_thresholds
                    and scores[category] > category_thresholds[category]
                ):
                    flagged = category
            if flagged:
                result.append((flagged, Range(start=pos, end=pos + len(chunk))))
            pos += len(chunk)
        return result
