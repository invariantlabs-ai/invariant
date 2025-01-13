from dataclasses import dataclass

from invariant.analyzer.runtime.functions import cache
from invariant.analyzer.stdlib.invariant.nodes import LLM

PII_ANALYZER = None


@dataclass
class PIIException(Exception):
    llm_call: LLM


def add_ranges(obj, results: list, interpreter):
    for res in results:
        interpreter.mark(obj, res.start, res.end)
    return [res.entity_type for res in results]


def get_entities(results: list):
    return [res.entity_type for res in results]


@cache
def pii(data: str | list, entities: list[str] | None = None) -> list[str]:
    """Predicate which detects PII in the given data.

    Returns the list of PII detected in the data.

    Supported data types:
    - str: A single message
    """
    global PII_ANALYZER
    if PII_ANALYZER is None:
        from invariant.analyzer.runtime.utils.pii import PII_Analyzer

        PII_ANALYZER = PII_Analyzer()

    from invariant.analyzer.runtime.evaluation import Interpreter

    interpreter = Interpreter.current()

    if type(data) is str:
        results = PII_ANALYZER.detect_all(data, entities)
        add_ranges(data, results, interpreter)
        return get_entities(results)

    if type(data) is not list:
        data = [data]

    all_pii = []
    for message in data:
        if message.content is None:
            continue
        results = PII_ANALYZER.detect_all(message.content, entities)
        add_ranges(message, results, interpreter)
        all_pii.extend(get_entities(results))
    return all_pii
