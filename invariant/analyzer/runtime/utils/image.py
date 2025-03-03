from typing import Tuple, Literal, List
import base64
import io
from PIL import Image, ImageDraw
from invariant.analyzer.extras import anthropic_extra


def add_rectangles_to_image(
    image: str,
    coordinates: list[tuple[int, int]],
    color: str = "red",
    border_width: int = 3,
    box_width: int = 10,
    image_format: Literal["jpeg", "png"] = "png",
) -> str:
    """Add multiple rectangles to a base64 encoded image.

    Args:
        image: The base64 encoded image.
        coordinates: The coordinates of the rectangles. Between 0 and 1.

    Returns:
        The base64 encoded image with the rectangles added.
    """
    image = Image.open(io.BytesIO(base64.b64decode(image)))
    draw = ImageDraw.Draw(image)

    for coordinate in coordinates:
        draw.rectangle(
            (
                coordinate[0] * image.width - box_width // 2,
                coordinate[1] * image.height - box_width // 2,
                coordinate[0] * image.width + box_width // 2,
                coordinate[1] * image.height + box_width // 2,
            ),
            outline=color,
            width=border_width,
        )

    # Convert the image back to a base64 string
    buffered = io.BytesIO()
    image.save(buffered, format=image_format)
    base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return base64_image


CLICK_AVAILABLE_SYSTEM_PROMPT = """
You are an advanced image analysis model tasked with evaluating whether a click on a user interface element violates a given policy.

### Task:
You will be provided with an image showing a user interface and a policy. In the image, there will be a red rectangle that marks the location of a user click. You must analyze the image and the policy to determine if the clicked element (indicated by the red rectangle) violates the policy.

### Key Points:
- Focus only on the red rectangle, which represents the location of the click. This rectangle is not necessarily surrounding an element but indicates where the click occurred.
- Use the policy provided and the context from the image to decide whether the click violates the policy.

### Policy Format:
The policy will be provided as a string enclosed in <POLICY> and </POLICY> tags.

### Output Format:
Your response should always be structured in JSON with the following keys:
- `allowed`: <boolean>  # True if the click is allowed, False if the click violates the policy.
- `reason`: <string>    # Explanation for the decision (allowed or not allowed).

### Example Input/Output:
INPUT:
{
    "image": IMAGE,
    "policy": "<POLICY> Never click `Buy` buttons. </POLICY>"
}
RESPONSE:
{
    "allowed": true,
    "reason": "This click is allowed as it does not click a `Buy` button."
}

INPUT:
{
    "image": IMAGE,
    "policy": "<POLICY> Never click `Operations` buttons. </POLICY>"
}
RESPONSE:
{
    "allowed": false,
    "reason": "This click is not allowed as it clicks the `Operations` button."
}
"""

def format_image(
    base64_image: str,
    prompt: str | None = None,
    image_format: Literal["jpeg", "png"] = "png",
):
    """Given a base64 encoded image, return a message that can be sent to the LLM.

    Args:
        base64_image: The base64 encoded image.
        prompt: The prompt to add to the image.
        image_format: The format of the image.

    Returns:
        A message that can be sent to the LLM.
    """
    content = []

    # Add the image to the content
    content.append(
        {
            "type": "image",
            "source": {
                "type": "base64",
                "data": base64_image,
                "media_type": f"image/{image_format}",
            },
        }
    )

    # If the prompt is set, add it to the content
    if prompt is not None:
        content.append({"type": "text", "text": prompt})

    return {"role": "user", "content": content}


def format_policy(policy: str) -> dict:
    """Given a policy, return a message that can be sent to the LLM.

    Args:
        policy: The policy to format.

    Returns:
        A message that can be sent to the LLM.
    """
    return {"role": "user", "content": f'<POLICY> {policy} </POLICY>'}


class ClaudeModel:
    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-5-sonnet-20240620",
        max_tokens: int = 1000,
        system_prompt: str = CLICK_AVAILABLE_SYSTEM_PROMPT,
        image_format: Literal["jpeg", "png"] = "png",
        bbox_config: dict | None = None,
    ):
        """
        Args:
            api_key: The API key for the Anthropic API.
            model_name: The name of the model to use.
            max_tokens: The maximum number of tokens to generate.
            system_prompt: The system prompt to use.
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.image_format = image_format

        Anthropic = anthropic_extra.package("anthropic").import_names("Anthropic")
        self.client = Anthropic(api_key=self.api_key)
        self.bbox_config = bbox_config or {
            "color": "red",
            "border_width": 5,
            "box_width": 75,
        }

    def _format_request(self, image: Image.Image, policy: str) -> List[dict]:
        image_message = format_image(image, image_format=self.image_format)
        policy_message = format_policy(policy)
        return [image_message, policy_message]

    def _get_response(self, messages: List[dict]) -> str:
        """Get a response from the model using the stable API.

        Args:
            messages: The messages to send to the model.

        Returns:
            The response from the model.
        """
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=messages,
        )

        return response.content[0].text

    def evaluate(self, image: str, policy: str, click_coordinates: Tuple[float, float]) -> str:
        """Evaluate whether a click is allowed.

        Args:
            image: Base64 encoded image.
            policy: The policy to evaluate.
            click_coordinates: The coordinates of the click. Values are between 0 and 1.

        Returns:
            json object with fields according to prompt
        """
        assert 0 <= click_coordinates[0] <= 1 and 0 <= click_coordinates[1] <= 1, "Click coordinates must be between 0 and 1"
        print(image[:10], len(image), click_coordinates)
        image = add_rectangles_to_image(
            image,
            [click_coordinates],
            image_format=self.image_format,
            **self.bbox_config,
        )
        messages = self._format_request(image, policy)
        return self._get_response(messages)
