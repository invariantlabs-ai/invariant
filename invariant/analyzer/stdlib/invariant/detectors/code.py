from invariant.analyzer.runtime.functions import cache
from invariant.analyzer.runtime.utils.code import *

PYTHON_ANALYZER = None
SEMGREP_DETECTOR = None


@cache
def python_code(
    data: str | list | dict, ipython_mode=False, **config: dict
) -> PythonDetectorResult:
    """Predicate used to extract entities from Python code."""

    global PYTHON_ANALYZER
    if PYTHON_ANALYZER is None:
        PYTHON_ANALYZER = PythonCodeDetector()

    if type(data) is str:
        return PYTHON_ANALYZER.detect(data, **config)
    if type(data) is not list:
        data = [data]

    res = PythonDetectorResult()
    for message in data:
        if message.content is None:
            continue
        res.extend(PYTHON_ANALYZER.detect(message.content, **config))
    return res


@cache
def ipython_code(data: str | list | dict, **config: dict) -> PythonDetectorResult:
    """Predicate used to extract entities from IPython cell code."""
    return python_code(data, ipython_mode=True, **config)


@cache
def semgrep(data: str | list | dict, **config: dict) -> list[CodeIssue]:
    """Predicate used to run Semgrep on code."""

    global SEMGREP_DETECTOR
    if SEMGREP_DETECTOR is None:
        SEMGREP_DETECTOR = SemgrepDetector()

    if type(data) is str:
        return SEMGREP_DETECTOR.detect_all(data, **config)

    chat = (
        data if isinstance(data, list) else ([{"content": data}] if type(data) == str else [data])
    )

    res = []
    for message in chat:
        if message.content is None:
            continue
        res.extend(SEMGREP_DETECTOR.detect_all(message.content, **config))
    return res
