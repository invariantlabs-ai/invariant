from typing import Optional

from invariant.analyzer.runtime.functions import cached
from invariant.analyzer.runtime.nodes import text
from invariant.analyzer.runtime.utils.base import DetectorResult
from invariant.analyzer.runtime.utils.batching import BatchedDetector
from invariant.analyzer.runtime.utils.prompt_injections import (
    PromptInjectionAnalyzer,
    UnicodeDetector,
)

PROMPT_INJECTION_ANALYZER: Optional[BatchedDetector] = None
UNICODE_ANALYZER = None


@cached
async def prompt_injection(data: str | list | dict, **config: dict) -> bool:
    """Predicate used for detecting prompt injections in the given data.

    Available parameters in the config:

        - model: The model to use for prompt injection detection.
        - threshold: The threshold for the model score above which text is considered prompt injection.
    """
    global PROMPT_INJECTION_ANALYZER
    if PROMPT_INJECTION_ANALYZER is None:
        PROMPT_INJECTION_ANALYZER = PromptInjectionAnalyzer()

    for t in text(data):
        if await PROMPT_INJECTION_ANALYZER.adetect(t, **config):
            return True
    return False


def parse_unicode(obj, results: list[DetectorResult], interpreter) -> list[str]:
    for r in results:
        interpreter.mark(obj, r.start, r.end)
    results = [r.entity for r in results]
    return list(set(results))


@cached
def unicode(data: str | list | dict, categories: list[str] | None = None) -> bool:
    """Predicate used for detecting disallowed types of unicode characters in the given data."""
    assert data is not None, "cannot call unicode(...) on None"
    global UNICODE_ANALYZER
    if UNICODE_ANALYZER is None:
        UNICODE_ANALYZER = UnicodeDetector()

    from invariant.analyzer.runtime.evaluation import Interpreter

    interpreter = Interpreter.current()

    if type(data) is str:
        return parse_unicode(data, UNICODE_ANALYZER.detect_all(data, categories), interpreter)
    if type(data) is not list:
        data = [data]

    all_unicode = []
    for message in data:
        txt = message.content
        if txt is None:
            continue
        res = parse_unicode(txt, UNICODE_ANALYZER.detect_all(txt, categories), interpreter)
        all_unicode.extend(res)
    return all_unicode
