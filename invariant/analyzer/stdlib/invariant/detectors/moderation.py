from invariant.analyzer.runtime.functions import cache
from invariant.analyzer.runtime.utils.base import DetectorResult
from invariant.analyzer.runtime.utils.moderation import ModerationAnalyzer

MODERATION_ANALYZER = None


def parse_moderation(obj, results: list[DetectorResult], interpreter) -> bool:
    for r in results:
        interpreter.mark(obj, r.start, r.end)
    results = [r.entity for r in results]
    return len(results) > 0


@cache
def moderated(data: str | list | dict, **config: dict) -> bool:
    """Predicate which evaluates to true if the given data should be moderated.

    Available parameters in the config:
        text: The text to analyze.
        model: The classification model to use for moderation detection.
        default_threshold: The threshold for the model score above which text is considered to be moderated.
        cat_thresholds: A dictionary of category-specific thresholds.
    """
    global MODERATION_ANALYZER
    if MODERATION_ANALYZER is None:
        MODERATION_ANALYZER = ModerationAnalyzer()

    from invariant.analyzer.runtime.evaluation import Interpreter

    interpreter = Interpreter.current()

    if type(data) is str:
        return parse_moderation(data, MODERATION_ANALYZER.detect_all(data, **config), interpreter)
    if type(data) is not list:
        data = [data]

    moderated = False
    for message in data:
        if message is None or message.content is None:
            continue
        if parse_moderation(
            message.content, MODERATION_ANALYZER.detect_all(message.content, **config), interpreter
        ):
            moderated = True
    return moderated
