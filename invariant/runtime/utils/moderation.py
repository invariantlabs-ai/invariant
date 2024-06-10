from invariant.runtime.utils.base import BaseDetector
from typing import Optional
from typing_extensions import override


DEFAULT_MODERATION_MODEL = "KoalaAI/Text-Moderation"

MODERATION_CATEGORIES = {
    "sexual": "S",
    "hate": "H",
    "violence": "V",
    "harassment": "HR",
    "self-harm": "SH",
    "sexual/minors": "S3",
    "hate/threatening": "H2",
    "violence/graphic": "V2",
}

MODERATION_CATEGORIES_INV = {v: k for k, v in MODERATION_CATEGORIES.items()}

class ModerationAnalyzer(BaseDetector):

    def __init__(self):
        self.pipe_store = {}
        
    def _load_model(self, model):
        from transformers import pipeline
        self.pipe_store[model] = pipeline("text-classification", model=model, top_k=None)

    def _has_model(self, model):
        return model in self.pipe_store

    def detect(self, text: str, model=DEFAULT_MODERATION_MODEL, default_threshold=0.5, cat_thresholds: Optional[dict]=None) -> bool:
        """Detects whether the text matches any of the categories that should be moderated.

        Args:
            text: The text to analyze.
            model: The model to use for moderation detection.
            default_threshold: The threshold for the model score above which text is considered to be moderated.
            cat_thresholds: A dictionary of category-specific thresholds.

        Returns:
            A boolean indicating whether the text should be moderated.
        """
        if not self._has_model(model):
            self._load_model(model)
        scores = self.pipe_store[model](text)
        score_map = {MODERATION_CATEGORIES_INV[score["label"]]: score["score"] for score in scores[0] if score["label"] != "OK"}
        for cat in MODERATION_CATEGORIES:
            if score_map[cat] > default_threshold:
                return True
            if cat_thresholds and cat in cat_thresholds and score_map[cat] > cat_thresholds[cat]:
                return True
        return False

