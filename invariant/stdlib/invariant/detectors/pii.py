from dataclasses import dataclass
from invariant.stdlib.invariant.nodes import LLM
from invariant.runtime.functions import cache

PII_ANALYZER = None

@dataclass
class PIIException(Exception):
    llm_call: LLM

@cache
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

    if type(data) is str:
        return PII_ANALYZER.detect_all(data)
    if type(data) is not list:
        data = [data]
    
    all_pii = []
    for message in data:
        if message.content is None:
            continue
        all_pii.extend(PII_ANALYZER.detect_all(message.content))
    return all_pii
