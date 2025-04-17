from invariant.analyzer.runtime.functions import cached
from invariant.analyzer.runtime.nodes import text
from invariant.analyzer.runtime.utils.sentence_similarity import (
    SentenceSimilarityAnalyzer,
)
from typing import Literal


SENTENCE_SIMILARITY_ANALYZER: SentenceSimilarityAnalyzer | None = None


@cached
async def embedding_similarity(
    data: str | list[str] | dict,
    target:  str | list[str] | dict,
    mode: Literal["min", "max"] = "max",
) -> float:
    """Return sentence similarity between data and target.
    If multiple data or target elements are provided, the function will return the
    minimum or maximum similarity score, depending on the mode

    Args:
        data: The input text(s).
        target: The target text(s) to compare against.
        mode: The mode to use for similarity detection. Can be either "min" or "max".
    Returns:
        The similarity score between the data and target, if multiple elements are provided,
        the function will return the minimum or maximum similarity score, depending on the mode.
    """
    data = text(data)
    target = text(target)
    global SENTENCE_SIMILARITY_ANALYZER
    if SENTENCE_SIMILARITY_ANALYZER is None:
        SENTENCE_SIMILARITY_ANALYZER = SentenceSimilarityAnalyzer()
    
    response = await SENTENCE_SIMILARITY_ANALYZER.adetect(
        data=data,
        target=target,
    )
    if mode == "min":
        return min([min(r) for r in response])
    elif mode == "max":
        return max([max(r) for r in response])
    else:
        raise ValueError("mode must be either 'min' or 'max'")

@cached
async def is_similar(
    data: str | list[str] | dict,
    target: str | list[str] | dict,
    threshold: float | Literal["might_resemble", "same_topic", "very_similar"] = "might_resemble",
) -> bool:
    """Predicate used for detecting whether the given data is similar to some target.
    If data is a list, and target is a list, the function will return true if any
    of the data elements are similar to any of the target elements.

    Args:
        data: The input text(s).
        target: The target text(s) to compare against.
        threshold: The threshold for witch two sentences are considered similar.
            Can either be a numerical value between 0 and 1, or "might_resemble", "same_topic", "very_similar".
    Returns:
        Boolean indicating whether data is similar to the target.
    """
    threshold_float = threshold if isinstance(threshold, float) else {
        "might_resemble": 0.2,
        "same_topic": 0.5,
        "very_similar": 0.8,
    }[threshold]
    similarity = await embedding_similarity(data, target, mode="max")
    return similarity > threshold_float
