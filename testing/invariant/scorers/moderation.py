from typing import Optional, Tuple

from invariant.custom_types.addresses import Range
from invariant.scorers.utils.base import BaseDetector

DEFAULT_MODERATION_MODEL = "OpenAI"

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
    },
    "KoalaAI/Text-Moderation": {
        "HR": "harassment",
        "H": "hate",
        "SH": "self-harm",
        "S": "sexual",
        "V": "violence",
        "S3": "sexual/minors",
        "H2": "hate/threatening",
        "V2": "violence/graphic",
    },
}

MODERATION_CATEGORIES_INV = {
    provider: {v: k for k, v in provider_mapping.items()}
    for provider, provider_mapping in MODERATION_CATEGORIES.items()
}


class ModerationAnalyzer(BaseDetector):
    def __init__(self):
        pass

    def _load_model(self, model):
        if model == "OpenAI":
            return

    def _has_model(self, model):
        return True

    def moderate_openai(self, client, text: str):
        # NOTE: OpenAI suggests: for higher accuracy, try splitting long pieces of text into smaller chunks each less than 2,000 characters.
        moderated = client.moderations.create(input=text)
        scores = moderated.results[0].category_scores.to_dict()
        scores = {
            MODERATION_CATEGORIES["OpenAI"][cat]: score
            for cat, score in scores.items()
            if cat in MODERATION_CATEGORIES["OpenAI"]
        }
        return scores

    def detect_all(
        self,
        text: str,
        split="\n",
        model=DEFAULT_MODERATION_MODEL,
        default_threshold=0.5,
        cat_thresholds: Optional[dict] = None,
    ) -> list[Tuple[str, Range]]:
        """Detects whether the text matches any of the categories that should be moderated.

        Args:
            text: The text to analyze.
            split: The delimiter to split the text into chunks.
            model: The model to use for moderation detection.
            default_threshold: The threshold for the model score above which text is considered to be moderated.
            cat_thresholds: A dictionary of category-specific thresholds.

        Returns:
            A list of (category, range) objects, each representing a substring that should be moderated.
        """
        if not self._has_model(model):
            self._load_model(model)

        # split by a delimiter
        # TODO: Invariant Language doesn't support split=\n, so let's always split for now
        if split is not None:
            text_splits = [
                split + chunk if i > 0 else chunk
                for i, chunk in enumerate(text.split(split))
            ]
        else:
            text_splits = [text]

        # split into chunks of 2000 characters (suggested by OpenAI)
        text_chunks = []
        for chunk in text_splits:
            if len(chunk) > 2000:
                text_chunks.extend(
                    [chunk[i : i + 2000] for i in range(0, len(chunk), 2000)]
                )
            else:
                text_chunks.append(chunk)

        assert len(text) == sum([len(chunk) for chunk in text_chunks])

        res = []
        pos = 0
        if model == "OpenAI":
            import openai

            client = openai.Client()
        for chunk in text_chunks:
            if model == "OpenAI":
                scores = self.moderate_openai(client, chunk)
            else:
                raise ValueError(f"Model {model} not supported.")

            flagged = None
            for cat in MODERATION_CATEGORIES_INV[model]:
                if scores[cat] > default_threshold:
                    flagged = cat
                if (
                    cat_thresholds
                    and cat in cat_thresholds
                    and scores[cat] > cat_thresholds[cat]
                ):
                    flagged = cat
            if flagged:
                res.append((flagged, Range(start=pos, end=pos + len(chunk))))
            pos += len(chunk)
        return res
