from typing import Optional

from invariant.scorers.strings import embedding_similarity


class ApproxString(str):
    """String class that allows for approximate comparisons using embedding similarity."""

    def __new__(cls, value, threshold: Optional[float] = None):
        instance = super(ApproxString, cls).__new__(cls, value)
        instance.threshold = threshold if threshold is not None else 0.5
        return instance

    def __eq__(self, other: str) -> bool:
        sim = embedding_similarity(self, other)
        return sim >= self.threshold

    def __ne__(self, other: str) -> bool:
        return not self.__eq__(other)


def approx(expected: str, threshold: Optional[float] = None) -> ApproxString:
    """Create an ApproxString object with a given threshold."""
    if type(expected) == str:
        return ApproxString(expected, threshold)
    else:
        raise ValueError("expected must be a string")
