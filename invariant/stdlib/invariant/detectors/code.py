from invariant.runtime.utils.code import PythonCodeDetector, PythonDetectorResult

PYTHON_ANALYZER = None

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