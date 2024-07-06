from invariant.runtime.utils.prompt_injections import PromptInjectionAnalyzer, UnicodeDetector
from invariant.runtime.functions import cache

PROMPT_INJECTION_ANALYZER = None
UNICODE_ANALYZER = None

@cache
def prompt_injection(data: str | list | dict, **config: dict) -> bool:
    """Predicate used for detecting prompt injections in the given data.

    Available parameters in the config:

        - model: The model to use for prompt injection detection.
        - threshold: The threshold for the model score above which text is considered prompt injection.
    """
    global PROMPT_INJECTION_ANALYZER
    if PROMPT_INJECTION_ANALYZER is None:
        PROMPT_INJECTION_ANALYZER = PromptInjectionAnalyzer()

    if type(data) is str:
        return PROMPT_INJECTION_ANALYZER.detect_all(data, **config)
    if type(data) is not list:
        data = [data]

    for message in data:
        if message.content is None:
            continue
        if PROMPT_INJECTION_ANALYZER.detect(message.content, **config):
            return True
    return False

@cache
def unicode(data: str | list | dict, **config: dict) -> bool:
    """Predicate used for detecting disallowed types of unicode characters in the given data."""
    assert data is not None, "cannot call unicode(...) on None"
    global UNICODE_ANALYZER
    if UNICODE_ANALYZER is None:
        UNICODE_ANALYZER = UnicodeDetector()

    if type(data) is str:
        return UNICODE_ANALYZER.detect_all(data, **config)
    if type(data) is not list:
        data = [data]

    all_unicode = []
    for message in data:
        if message.content is None:
            continue
        res = UNICODE_ANALYZER.detect_all(message.content, **config)
        all_unicode.extend(UNICODE_ANALYZER.get_entities(res))
    return all_unicode
