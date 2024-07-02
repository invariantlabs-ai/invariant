import json
from dataclasses import dataclass
from invariant.stdlib.invariant.nodes import LLM

PII_ANALYZER = None

@dataclass
class PIIException(Exception):
    llm_call: LLM

def pii(data: str | list, **config):
    """Predicate which detects PII in the given data.
    
    Returns the list of PII detected in the data.

    Supported data types:
    - str: A single message
    """
    global PII_ANALYZER
    if PII_ANALYZER is None:
        from invariant.runtime.utils.pii import PII_Analyzer
        PII_ANALYZER = PII_Analyzer()

    chat = data if isinstance(data, list) else ([{"content": data}] if type(data) == str else [data])
    
    all_pii = []
    for message in chat:
        if message is None:
            continue
        if "content" not in message:
            content = json.dumps(message)
        elif message["content"] is None:
            continue
        else:
            content = message["content"]
        all_pii.extend(PII_ANALYZER.detect_all(content))
    return all_pii