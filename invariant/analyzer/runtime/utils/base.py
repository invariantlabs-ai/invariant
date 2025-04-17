from pydantic import Field
from pydantic.dataclasses import dataclass
from openai import AsyncClient


client: AsyncClient | None = None
def get_openai_client() -> AsyncClient:
    """Get an OpenAI client for making requests."""
    global client
    if client is None:
        client = AsyncClient()
    return client


@dataclass
class DetectorResult:
    entity: str = Field(..., description="The type of entity that was detected.")
    start: int = Field(..., description="The start index of the detected entity.")
    end: int = Field(..., description="The end index of the detected entity.")


class BaseDetector:
    """Base class for detectors."""

    def get_entities(self, results: list[DetectorResult]) -> list[str]:
        """Returns a list of entities from a list of DetectorResult objects.

        Args:
            results: A list of DetectorResult objects.
        Returns:
            A list of entities.
        """
        return [result.entity for result in results]

    def detect_all(self, text: str, *args, **kwargs) -> list[DetectorResult]:
        """Performs detection on the given text and returns a list of DetectorResult objects.

        Args:
            text: The text to analyze.
        Returns:
            A list of DetectorResult objects.
        """
        raise NotImplementedError("")

    def detect(self, text: str, *args, **kwargs) -> bool:
        """Performs detection on the given text and returns a boolean indicating whether there has been any detection.

        Args:
            text: The text to analyze.
        Returns:
            A boolean indicating whether there has been any detection.
        """
        return len(self.detect_all(text, *args, **kwargs)) > 0

    async def preload(self):
        """
        Some workload to run to initialize the detector for lower-latency inference later on.

        For instance, model loading or other expensive operations.
        """
        pass
