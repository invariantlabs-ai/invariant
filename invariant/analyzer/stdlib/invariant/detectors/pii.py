from dataclasses import dataclass

from invariant.analyzer.runtime.functions import cached
from invariant.analyzer.runtime.nodes import text
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


@cached
def _pii_detect(data: str | list, entities: list[str] | None = None) -> list[str]:
    global PII_ANALYZER
    if PII_ANALYZER is None:
        from invariant.analyzer.runtime.utils.pii import PII_Analyzer

        PII_ANALYZER = PII_Analyzer()

    return PII_ANALYZER.detect_all(data, entities)


async def pii(data: str | list, entities: list[str] | None = None) -> list[str]:
    """Predicate which detects PII in the given data.

    Returns the list of PII detected in the data.

    Supported data types:
    - str: A single message
    """
    from invariant.analyzer.runtime.evaluation import Interpreter

    interpreter = Interpreter.current()

    all_pii = []
    for t in text(data):
        results = await _pii_detect(t, entities)
        add_ranges(t, results, interpreter)
        all_pii.extend(get_entities(results))

    return all_pii
