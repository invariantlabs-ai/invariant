import os
import shutil


def system(content):
    return {"role": "system", "content": content}


def user(content):
    return {"role": "user", "content": content}


def assistant(content, tool_call=None):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": ([tool_call] if tool_call is not None else []),
    }


def tool_call(tool_call_id, function_name, arguments):
    return {
        "id": tool_call_id,
        "type": "function",
        "function": {"name": function_name, "arguments": arguments},
    }


def tool(tool_call_id, content):
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def is_program_installed(program_name: str) -> bool:
    """Check if a program is installed and available in the system PATH.

    Args:
        program_name (str): The name of the program to check for

    Returns:
        bool: True if the program is installed and accessible, False otherwise

    """
    return shutil.which(program_name) is not None


def is_remote_run() -> bool:
    """Check if policies are evaluated server-side, not in this process.

    i.e. LOCAL_POLICY != 1

    Returns:
        bool: True if policies are evaluated server-side, False otherwise

    """
    return os.environ.get("LOCAL_POLICY", "0") != "1"
