from invariant.runtime.utils.moderation import ModerationAnalyzer

MODERATION_ANALYZER = None

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

    chat = data if isinstance(data, list) else ([{"content": data}] if type(data) == str else [data])
    
    for message in chat:
        if message is None:
            continue
        if message["content"] is None:
            continue
        if MODERATION_ANALYZER.detect(message["content"], **config):
            return True

    return False


    