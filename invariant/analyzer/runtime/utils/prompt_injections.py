import unicodedata

from invariant.analyzer.extras import transformers_extra
from invariant.analyzer.runtime.utils.base import BaseDetector, DetectorResult
from invariant.analyzer.runtime.utils.batching import BatchedDetector

DEFAULT_PI_MODEL = "protectai/deberta-v3-base-prompt-injection-v2"


class PromptInjectionAnalyzer(BatchedDetector):
    """Analyzer for detecting prompt injections via classifier.

    The analyzer uses a pre-trained classifier (e.g., a model available on Huggingface) to detect prompt injections in text.
    Note that this is just a heuristic, and relying solely on the classifier is not sufficient to prevent the security vulnerabilities.
    """

    def __init__(self):
        super().__init__(max_batch_size=16, max_wait_time=0.1)
        self.pipe_store = dict()

    async def preload(self):
        # preloads the model
        await self.adetect("Testing")

    def _load_model(self, model):
        pipeline = transformers_extra.package("transformers").import_names("pipeline")
        self.pipe_store[model] = pipeline("text-classification", model=model, top_k=None)

    def _get_model(self, model):
        return self.pipe_store[model]

    def _has_model(self, model):
        return model in self.pipe_store

    async def adetect_all_batch(
        self, texts: list[str], model: str = DEFAULT_PI_MODEL, threshold: float = 0.9
    ) -> bool:
        """Detects whether text contains prompt injection.

        Args:
            text: The text to analyze.
            model: The model to use for prompt injection detection.
            threshold: The threshold for the model score above which text is considered prompt injection.

        Returns:
            A boolean indicating whether the text contains prompt injection.
        """
        if not self._has_model(model):
            self._load_model(model)

        # make sure texts is list of str
        assert type(texts) is list and all(
            type(t) is str for t in texts
        ), "texts must be a list of str"

        model = self._get_model(model)
        scores = model(texts)

        return [
            [scores[i][0]["label"] == "INJECTION" and scores[i][0]["score"] > threshold]
            for i in range(len(scores))
        ]

    async def adetect(self, text, *args, **kwargs):
        result = await self.adetect_all(text, *args, **kwargs)
        return result[0] is True


DEFAULT_PI_MODEL = "ProtectAI/deberta-v3-base-prompt-injection-v2"


class UnicodeDetector(BaseDetector):
    """Detector for detecting unicode characters based on their category (using allow or deny list).

    The detector analyzes the given string character by character and considers the following categories during the detection:

    [Cc]	Other, Control
    [Cf]	Other, Format
    [Cn]	Other, Not Assigned (no characters in the file have this property)
    [Co]	Other, Private Use
    [Cs]	Other, Surrogate
    [LC]	Letter, Cased
    [Ll]	Letter, Lowercase
    [Lm]	Letter, Modifier
    [Lo]	Letter, Other
    [Lt]	Letter, Titlecase
    [Lu]	Letter, Uppercase
    [Mc]	Mark, Spacing Combining
    [Me]	Mark, Enclosing
    [Mn]	Mark, Nonspacing
    [Nd]	Number, Decimal Digit
    [Nl]	Number, Letter
    [No]	Number, Other
    [Pc]	Punctuation, Connector
    [Pd]	Punctuation, Dash
    [Pe]	Punctuation, Close
    [Pf]	Punctuation, Final quote (may behave like Ps or Pe depending on usage)
    [Pi]	Punctuation, Initial quote (may behave like Ps or Pe depending on usage)
    [Po]	Punctuation, Other
    [Ps]	Punctuation, Open
    [Sc]	Symbol, Currency
    [Sk]	Symbol, Modifier
    [Sm]	Symbol, Math
    [So]	Symbol, Other
    [Zl]	Separator, Line
    [Zp]	Separator, Paragraph
    [Zs]	Separator, Space
    """

    def detect_all(self, text: str, categories: list[str] | None = None) -> list[DetectorResult]:
        """Detects all unicode groups that should not be allowed in the text.

        Attributes:
            allow: List of categories to allow.
            deny: List of categories to deny.

        Returns:
            A list of DetectorResult objects indicating the detected unicode groups.

        Raises:
            ValueError: If both allow and deny categories are specified.
        """
        res = []
        for index, chr in enumerate(text):
            cat = unicodedata.category(chr)
            if categories is None or cat in categories:
                res.append(DetectorResult(cat, index, index + 1))
        return res
