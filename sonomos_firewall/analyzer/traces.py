"""
Utility functions for creating trace messages.
"""


def system(content):
    return {"role": "system", "content": content}


def user(content, chunked=False):
    if chunked:
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": str(content)},
            ],
        }
    return {"role": "user", "content": content}


def assistant(content, tool_call=None):
    if not isinstance(tool_call, list):
        tool_call = [tool_call] if tool_call is not None else []

    return {
        "role": "assistant",
        "content": content,
        "tool_calls": tool_call,
    }


def image(image_url):
    return {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
        ],
    }


def tool_call(tool_call_id, function_name, arguments):
    return {
        "id": tool_call_id,
        "type": "function",
        "function": {"name": function_name, "arguments": arguments},
    }


def tool(tool_call_id, content):
    return {"role": "tool", "tool_call_id": tool_call_id, "content": str(content)}


def chunked(msg):
    """
    Helper function to turn a message with direct string content, into a chunked
    multi-part message.

    This is useful to test guardrailing behavior for both, chunked and non-chunked
    message content.
    """
    if not isinstance(msg["content"], str):
        raise ValueError("Message content must be a string to be chunked.")

    updated = {**msg}
    updated["content"] = [
        {"type": "text", "text": msg["content"]},
    ]

    return updated
