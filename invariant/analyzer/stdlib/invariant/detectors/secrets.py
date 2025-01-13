from invariant.analyzer.runtime.functions import cache
from invariant.analyzer.runtime.utils.secrets import SecretsAnalyzer

SECRETS_ANALYZER = None


@cache
def secrets(data: str | list | dict, **config: dict) -> list[str]:
    """Predicate which evaluates to true if the given data should be moderated.

    Available parameters in the config:
        text: The text to analyze.
        model: The classification model to use for moderation detection.
        default_threshold: The threshold for the model score above which text is considered to be moderated.
        cat_thresholds: A dictionary of category-specific thresholds.
    """
    global SECRETS_ANALYZER
    if SECRETS_ANALYZER is None:
        SECRETS_ANALYZER = SecretsAnalyzer()

    if type(data) is str:
        return SECRETS_ANALYZER.detect_all(data, **config)

    chat = (
        data if isinstance(data, list) else ([{"content": data}] if type(data) == str else [data])
    )

    all_secrets = []
    for message in chat:
        if message is None:
            continue
        if message.content is None:
            continue

        res = SECRETS_ANALYZER.detect_all(message.content, **config)
        all_secrets.extend(SECRETS_ANALYZER.get_entities(res))
    return all_secrets
