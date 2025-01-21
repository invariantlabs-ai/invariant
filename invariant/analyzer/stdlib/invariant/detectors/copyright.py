from invariant.analyzer.runtime.functions import cache

COPYRIGHT_ANALYZER = None


@cache
def copyright(data: str | list, **config) -> list[str]:
    """Predicate which detects PII in the given data.

    Returns the list of PII detected in the data.

    Supported data types:
    - str: A single message
    """
    global COPYRIGHT_ANALYZER
    if COPYRIGHT_ANALYZER is None:
        from invariant.analyzer.runtime.utils.copyright.copyright import CopyrightAnalyzer

        COPYRIGHT_ANALYZER = CopyrightAnalyzer()

    if type(data) is str:
        return COPYRIGHT_ANALYZER.get_entities(COPYRIGHT_ANALYZER.detect_all(data))
    if type(data) is not list:
        data = [data]

    all_copyright = []
    for message in data:
        if message.content is None:
            continue
        res = COPYRIGHT_ANALYZER.detect_all(message.content)
        all_copyright.extend(COPYRIGHT_ANALYZER.get_entities(res))
    return all_copyright
