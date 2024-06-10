from dataclasses import dataclass
from invariant.stdlib.invariant.nodes import LLM

PII_ANALYZER = None

@dataclass
class PIIException(Exception):
    llm_call: LLM

def pii(data: str | list, **config):
    """Predicate which detects PII in the given data."""
    global PII_ANALYZER
    if PII_ANALYZER is None:
        from invariant.runtime.utils.pii import PII_Analyzer
        PII_ANALYZER = PII_Analyzer()

    chat = data if isinstance(data, list) else ([{"content": data}] if type(data) == str else [data])
    
    all_pii = []
    for message in chat:
        if message is None:
            continue
        if message["content"] is None:
            continue
        all_pii.extend(PII_ANALYZER.detect_all(message["content"]))
        return all_pii