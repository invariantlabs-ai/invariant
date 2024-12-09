import re

from nltk.metrics.distance import edit_distance

from invariant.scorers.utils.embeddings import cosine_similarity, get_embedding


def levenshtein(str1: str, str2: str) -> float:
    """Compute the normalized score using Levenshtein (edit) distance between two strings
    as 1 - distance / max(len(str1), len(str2)).
    """
    if len(str1) == 0 or len(str2) == 0:
        return 1.0 if str1 == str2 else 0.0
    edit_dist = edit_distance(str1, str2)
    return 1 - edit_dist / max(len(str1), len(str2))


def embedding_similarity(str1: str, str2: str) -> float:
    """Compute cosine similarity between two text strings."""
    v1 = get_embedding(str1)
    v2 = get_embedding(str2)
    return cosine_similarity(v1, v2)


def contains(text: str, pattern: str) -> bool:
    """Check if a text contains a regex pattern."""
    return re.search(pattern, text) is not None
