"""A JSON formatter for highlighting parts of the trace in the pytest output.

It supports pretty-printing of JSON objects
in a format, where non-highlighted lines are commented out using
Python-style '#' comments.

This allows us to highlight sub-objects in a JSON object in the
highlighted pytest output, while keeping the rest of the JSON
object in the output for context.
"""

import json

MAX_LEN = 1000


def format_trace(json_obj, highlights=[]):
    """Pretty-print a JSON-like object with the given highlights.

    JSON-like means Python objects that can be serialized to JSON (dict, list, str, int, etc.).

    Does not support character ranges, but will highlight complete
    JSON nodes (e.g. full strings, numbers, objects, lists).

    Args:
        json_obj: The JSON object to format (dict, list, number, string, etc.).
        highlights: A list of paths to highlight in the JSON object (e.g. "0.content").
    """
    result = _format_trace(json_obj, highlights=highlights)
    updated = []

    for line in result.split("\n"):
        is_comment = line.lstrip().startswith("#")
        # if is_comment, remove first #, otherwise add a space
        if is_comment:
            # replace first occurence of # with a space
            line = line.replace("#", " ", 1)
        else:
            line = " " + line

        # comment out the inverse of the highlights
        updated.append(("#" if not is_comment else " ") + line)

    start = None
    end = len(updated)
    for i in range(len(updated)):
        if start is None and not updated[i].lstrip().startswith("#"):
            start = i
        if not updated[i].lstrip().startswith("#"):
            end = i + 1
    start = max(0, (start or 0) - 5)
    end = min(len(updated), end + 5)

    return "\n".join(updated[start:end])


def strip_comment(line):
    """Replace the starting comment in a line with a space."""
    if line.lstrip().startswith("#"):
        return True, line.replace("#", " ", 1)
    return False, line


def _format_str(s: str):
    if s.startswith("local_base64_img"):
        return "<base64_image>"
    elif len(s) > MAX_LEN:
        return s[: MAX_LEN // 2] + "..." + s[-MAX_LEN // 2 :]
    return s


def _format_trace(json_obj, indent="", path=[], highlights=[]):
    """Format a JSON object as a string."""
    path_str = ".".join(map(str, path))
    is_highlighted = path_str in highlights or "*" in highlights
    highlight_line = (
        ""  # ("\n" + " " * len(indent) + "⌃" + "---------- </highlighted> ----------")
    )

    if type(json_obj) is dict:
        entries = []
        for k, v in json_obj.items():
            value = _format_trace(v, indent + "  ", path + [k], highlights=highlights)
            has_comment, value = strip_comment(value)
            comment = "#" if has_comment else ""
            entries.append(f"{comment}{indent}  {k}: {value}\n")

        value_repr = (
            # (f"---- <highlighted> ----\n{indent}" if is_highlighted else "")
            "{\n"
            + "".join(entries)
            + f"{indent}}}"
            + (highlight_line if is_highlighted else "")
        )
    elif type(json_obj) is list:
        value_repr = (
            # (f"---- <highlighted> ----\n{indent}" if is_highlighted else "")
            "[\n"
            + "".join(
                f"{indent}  {_format_trace(v, indent + '  ', path + [i], highlights=highlights)},\n"
                for i, v in enumerate(json_obj)
            )
            + f"{indent}]"
            + (highlight_line if is_highlighted else "")
        )
    elif type(json_obj) is str:
        value_repr = json.dumps(_format_str(json_obj), ensure_ascii=False)
    else:
        value_repr = json.dumps(json_obj, ensure_ascii=False)

    lines = value_repr.split("\n")

    if is_highlighted:
        lines = ["#" + " " + line for i, line in enumerate(lines)]
    else:
        lines = [" " + line for line in lines]

    value_repr = "\n".join(lines)

    return value_repr
