from invariant.analyzer.runtime.functions import cached

COPYRIGHT_ANALYZER = None


@cached
def copyright(data: str | list, **config) -> list[str]:
    """Predicate which detects PII in the given data.

    Returns the list of PII detected in the data.

    Supported data types:
    - str: A single message
    """
    from invariant.analyzer.stdlib.invariant.builtins import text

    global COPYRIGHT_ANALYZER
    if COPYRIGHT_ANALYZER is None:
        from invariant.analyzer.runtime.utils.copyright.copyright import CopyrightAnalyzer

        COPYRIGHT_ANALYZER = CopyrightAnalyzer()

    all_copyright = []
    for t in text(data):
        if t is None:
            continue
        res = COPYRIGHT_ANALYZER.detect_all(t)
        all_copyright.extend(COPYRIGHT_ANALYZER.get_entities(res))
    return all_copyright
