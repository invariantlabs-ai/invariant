def system(content):
    return {"role": "system", "content": content}

def user(content):
    return {"role": "user", "content": content}

def assistant(content, tool_call=None):
    return {"role": "assistant", "content": None, "tool_calls": ([tool_call] if tool_call is not None else [])}

def tool_call(tool_call_id, function_name, arguments):
    return {
        "id": tool_call_id,
        "type": "function",
        "function": {
            "name": function_name,
            "arguments": arguments
        }
    }

def tool(tool_call_id, content):
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}
