from invariant.analyzer.runtime.utils.base import BaseDetector, get_openai_client
from invariant.analyzer.runtime.functions import cached
import asyncio

def matmul(A: list[list[float]], B: list[list[float]]) -> list[list[float]]:
    """Matrix multiplication of A and B.transpose."""
    res: list[list[float]] = []
    for i in range(len(A)):
        res.append([sum(a*b for a,b in zip(A[i], row)) for row in B])
    return res

@cached
async def embed(text: str, model: str) -> list[float]:
    """Get embeddings for the given text using the specified model."""
    response = await get_openai_client().embeddings.create(
        input=text, model=model.split("/")[1], encoding_format="float"
    )
    return response.data[0].embedding


class SentenceSimilarityAnalyzer(BaseDetector):
    """Analyzer for detecting sentence similarity using a hosted model."""

    def __init__(self):
        super().__init__()

    async def adetect(
        self,
        data: list[str],
        target: list[str],
        model: str = "openai/text-embedding-3-large",
    ) -> list[list[float]]:
        """Detects whether text contains prompt injection.

        Args:
            text: The text to analyze.
            model: The model to use for prompt injection detection.
            threshold: The threshold for the model score above which text is considered prompt injection.

        Returns:
            A boolean indicating whether the text contains prompt injection.
        """
        data_tasks = [embed(text=text, model=model) for text in data]
        target_docs_tasks = [
            embed(text=text, model=model) for text in target
        ]
        embeddings_data, embeddings_target_docs = await asyncio.gather(
            asyncio.gather(*data_tasks),
            asyncio.gather(*target_docs_tasks)
        )
        similarities = matmul(embeddings_data, embeddings_target_docs)
        return similarities
