from invariant.analyzer.runtime.functions import cache
from invariant.analyzer.runtime.utils.image import ClaudeModel
from typing import Dict, Tuple, Optional
import json
import os


# Global instance of the ClaudeModel
IMAGE_POLICY_MODEL = None

@cache
def image_policy_violations(
    data: str,
    policy: str,
    click_coordinates: Tuple[float, float],
    api_key: Optional[str] = None,
    model_name: str = "claude-3-7-sonnet-20250219",
    **config: Dict
) -> bool:
    """
    Detects policy violations in images using Claude's vision capabilities.

    Args:
        data: The image data as a base64 string. It may have a prefix like data:image/jpeg;base64, in which case it will be stripped.
        policy: The policy to evaluate against the image
        click_coordinates: coordinates for click evaluation (x, y) between 0 and 1
        api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY environment variable)
        model_name: The Claude model to use
        **config: Additional configuration options

    Returns:
        bool: True if the policy is violated, False otherwise
    """
    global IMAGE_POLICY_MODEL

    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return True

    # Initialize the model if not already done
    if IMAGE_POLICY_MODEL is None:
        IMAGE_POLICY_MODEL = ClaudeModel(
            api_key=api_key,
            model_name=model_name,
            **config
        )

    # Strip base64 prefix if present
    if data.startswith('data:image/'):
        # Find the base64 part after the comma
        base64_start = data.find(',')
        if base64_start != -1:
            data = data[base64_start + 1:]

    # Evaluate the image
    return _evaluate_single_image(data, policy, click_coordinates)

def _evaluate_single_image(
    image: str,
    policy: str,
    click_coordinates: Optional[Tuple[float, float]],
) -> bool:
    """Evaluate a single image against the policy."""
    try:
        response = IMAGE_POLICY_MODEL.evaluate(image, policy, click_coordinates)

        # Parse the response
        try:
            result = json.loads(response)
            return not result["allowed"]
        except json.JSONDecodeError:
            # If response is not valid JSON, create a result with the raw response
            return True
    except Exception as e:
        # Handle any exceptions during evaluation
        return True

