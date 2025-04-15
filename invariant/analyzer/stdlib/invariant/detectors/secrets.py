from invariant.analyzer.runtime.functions import cached
from invariant.analyzer.runtime.utils.secrets import SecretsAnalyzer

SECRETS_ANALYZER = None


@cached
def secrets(data: str | list | dict, **config: dict) -> list[str]:
    """Predicate which evaluates to true if the given data should be moderated.

    Available parameters in the config:
        text: The text to analyze.
        model: The classification model to use for moderation detection.
        default_threshold: The threshold for the model score above which text is considered to be moderated.
        cat_thresholds: A dictionary of category-specific thresholds.
    """
    from invariant.analyzer.stdlib.invariant.builtins import text

    global SECRETS_ANALYZER
    if SECRETS_ANALYZER is None:
        SECRETS_ANALYZER = SecretsAnalyzer()

    all_secrets = []
    for t in text(data):
        res = SECRETS_ANALYZER.detect_all(t, **config)
        all_secrets.extend(SECRETS_ANALYZER.get_entities(res))
    return all_secrets
