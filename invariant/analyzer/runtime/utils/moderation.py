import asyncio

from invariant.analyzer.extras import transformers_extra
from invariant.analyzer.runtime.utils.base import BaseDetector, DetectorResult

DEFAULT_MODERATION_MODEL = "KoalaAI/Text-Moderation"

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
        super().__init__()
        self.pipe_store = {}

    def _load_model(self, model):
        if model == "OpenAI":
            return
        pipeline = transformers_extra.package("transformers").import_names("pipeline")
        self.pipe_store[model] = pipeline("text-classification", model=model, top_k=None)

    async def preload(self):
        await self.adetect("hello there")

    def _has_model(self, model):
        return model in self.pipe_store

    async def moderate_openai(self, client, text: str):
        # NOTE: OpenAI suggests: for higher accuracy, try splitting long pieces of text into smaller chunks each less than 2,000 characters.
        moderated = await client.moderations.create(input=text)
        scores = moderated.results[0].category_scores.to_dict()
        scores = {
            MODERATION_CATEGORIES["OpenAI"][cat]: score
            for cat, score in scores.items()
            if cat in MODERATION_CATEGORIES["OpenAI"]
        }
        return scores

    async def moderate_koalaai(self, pipe, text: str):
        scores = pipe(text)
        scores = {
            MODERATION_CATEGORIES["KoalaAI/Text-Moderation"][score["label"]]: score["score"]
            for score in scores[0]
            if score["label"] != "OK"
        }
        return scores

    def detect(self, text, *args, **kwargs):
        return asyncio.run(self.adetect(text, *args, **kwargs))

    async def adetect(self, text, *args, **kwargs):
        """Detects whether the text matches any of the categories that should be moderated.

        Args:
            text: The text to analyze.
            split: The delimiter to split the text into chunks.
            model: The model to use for moderation detection.
            default_threshold: The threshold for the model score above which text is considered to be moderated.
            cat_thresholds: A dictionary of category-specific thresholds.

        Returns:
            A list of DetectorResult objects, each representing a substring that should be moderated.
        """
        split = kwargs.get("split", "\n")
        model = kwargs.get("model", DEFAULT_MODERATION_MODEL)
        default_threshold = kwargs.get("default_threshold", 0.5)
        cat_thresholds = kwargs.get("cat_thresholds", None)

        if not self._has_model(model):
            self._load_model(model)

        # split by a delimiter
        # TODO: Invariant Language doesn't support split=\n, so let's always split for now
        if split is not None:
            text_splits = [
                split + chunk if i > 0 else chunk for i, chunk in enumerate(text.split(split))
            ]
        else:
            text_splits = [text]

        # split into chunks of 2000 characters (suggested by OpenAI)
        text_chunks = []
        for chunk in text_splits:
            if len(chunk) > 2000:
                text_chunks.extend([chunk[i : i + 2000] for i in range(0, len(chunk), 2000)])
            else:
                text_chunks.append(chunk)

        assert len(text) == sum([len(chunk) for chunk in text_chunks])

        res = []
        pos = 0
        if model == "OpenAI":
            import openai

            client = openai.AsyncClient()
        for chunk in text_chunks:
            if model == "OpenAI":
                scores = await self.moderate_openai(client, chunk)
            elif model == "KoalaAI/Text-Moderation":
                scores = await self.moderate_koalaai(self.pipe_store[model], chunk)
            else:
                raise ValueError(f"Model {model} not supported.")

            flagged = None
            for cat in MODERATION_CATEGORIES_INV[model]:
                if scores[cat] > default_threshold:
                    flagged = cat
                if cat_thresholds and cat in cat_thresholds and scores[cat] > cat_thresholds[cat]:
                    flagged = cat
            if flagged:
                res.append(DetectorResult(flagged, pos, pos + len(chunk)))
            pos += len(chunk)

        return res
