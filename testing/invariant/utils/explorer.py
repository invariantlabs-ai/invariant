"""Utility functions to interact with the Invariant Explorer."""

import base64

import requests

TIMEOUT = 5  # connect and read timeouts.


def _get_image(
    local_img_path: str, explorer_endpoint: str = "https://explorer.invariantlabs.ai"
) -> str:
    """Get the base64 encoded image from the local_img_path.

    Args:
        local_img_path: The path to the image in the local filesystem.
    """
    path_parts = local_img_path.split("/")
    dataset_id = path_parts[-3]
    trace_id = path_parts[-2]
    image_id = path_parts[-1].split(".")[0]

    response = requests.get(
        f"{explorer_endpoint}/api/v1/trace/image/{dataset_id}/{trace_id}/{image_id}",
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        raise ValueError(
            f"Error getting image {local_img_path} from Explorer: {response.status_code}"
        )
    return base64.b64encode(response.content).decode("utf-8")


def from_explorer(
    identifier_or_id: str,
    index: int | None = None,
    explorer_endpoint: str = "https://explorer.invariantlabs.ai",
):
    """Loads a public trace from the Explorer (https://explorer.invariantlabs.ai).

    The identifier_or_id can be either a trace ID or a <username>/<dataset> pair, in which case
    the index of the trace to load must be provided.

    Args:
        identifier_or_id: The trace ID or <username>/<dataset> pair.
        index: The index of the trace to load from the dataset.
        explorer_endpoint: The endpoint of the Explorer API.

    Returns:
        A Trace object with the loaded trace.
    """

    metadata = {
        "id": identifier_or_id,
    }
    timeout = 5  # connect and read timeouts.

    if index is not None:
        username, dataset = identifier_or_id.split("/")

        trace_metadata = requests.get(
            url=f"{explorer_endpoint}/api/v1/dataset/byuser/{username}/{dataset}/traces?indices={index}",
            timeout=timeout,
        )
        if len(trace_metadata.json()) == 0:
            raise ValueError(
                "No trace with the specified index found for the <username>/<dataset> pair."
            )
        identifier_or_id = trace_metadata.json()[0]["id"]

        metadata.update(
            {
                "trace_id": identifier_or_id,
                "dataset": dataset,
                "username": username,
            }
        )
    else:
        if "/" in identifier_or_id:
            raise ValueError(
                "Please provide the index of the trace to select from the <username>/<dataset> pair."
            )

    response = requests.get(
        url=f"{explorer_endpoint}/api/v1/trace/{identifier_or_id}?annotated=1",
        timeout=TIMEOUT,
    )
    messages = response.json()["messages"]
    for msg in messages:
        if (
            (content := msg.get("content"))
            and isinstance(content, str)
            and content.startswith("local_img_link:")
        ):
            img = _get_image(msg["content"], explorer_endpoint)
            msg["content"] = "local_base64_img: " + img
    return messages, metadata
