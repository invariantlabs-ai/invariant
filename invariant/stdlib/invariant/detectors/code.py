from invariant.runtime.utils.code import *

PYTHON_ANALYZER = None
CODE_SHIELD_DETECTOR = None

def python_code(data: str | list | dict, **config: dict) -> PythonDetectorResult:
    """Predicate used to extract entities from Python code."""

    global PYTHON_ANALYZER
    if PYTHON_ANALYZER is None:
        PYTHON_ANALYZER = PythonCodeDetector()

    chat = data if isinstance(data, list) else ([{"content": data}] if type(data) == str else [data])
    
    res = None
    for message in chat:
        if message is None:
            continue
        if message["content"] is None:
            continue
        new_res = PYTHON_ANALYZER.detect(message["content"], **config)
        res = new_res if res is None else res.extend(new_res)
    return res


def code_shield(data: str | list | dict, **config: dict) -> list[CodeIssue]:
    """Predicate used to extract entities from Python code."""

    global CODE_SHIELD_DETECTOR
    if CODE_SHIELD_DETECTOR is None:
        CODE_SHIELD_DETECTOR = CodeShieldDetector()

    chat = data if isinstance(data, list) else ([{"content": data}] if type(data) == str else [data])
    
    res = None
    for message in chat:
        if message is None:
            continue
        if message["content"] is None:
            continue
        new_res = CODE_SHIELD_DETECTOR.detect_all(message["content"], **config)
        res = new_res if res is None else res.extend(new_res)
    return res
