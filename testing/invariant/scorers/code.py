"""Scoring functions for content that contains code."""

import json
import subprocess
import tempfile
from typing import Tuple

import openai
from invariant.custom_types.addresses import Range
from invariant.utils.packages import is_program_installed
from pydantic import BaseModel


def is_valid_json(text: str) -> Tuple[bool, int | None]:
    """Check if a string is valid JSON."""
    try:
        json.loads(text)
        return True, None
    except json.JSONDecodeError as e:
        return False, [Range.from_line(text, e.lineno - 1).to_address()]


def is_valid_python(text: str) -> Tuple[bool, int | None]:
    """Check if a string is valid Python code."""
    try:
        compile(text, "<string>", "exec")
        return True, None
    except SyntaxError as e:
        return False, [Range.from_line(text, e.lineno - 1).to_address()]
    except Exception:
        return False, None


class Dependencies(BaseModel):
    """Dependencies detected by the LLM."""

    dependencies: list[str]


def _get_dependencies(text: str) -> Dependencies:
    """Get the dependencies of a Python code snippet using an LLM."""
    prompt = f"""Extract the dependencies necessary to run the following python code (either include concrete versions, e.g. 1.0 or do not write versions at all):\n\n{
            text}"""
    client = openai.OpenAI()
    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format=Dependencies,
    )
    return response.choices[0].message.parsed


def execute(text: str, detect_packages: bool = False) -> str:
    """Executes a string of Python code and returns the standard output.

    Optionally, this function can also detect the dependencies of the code using an LLM and append them as a header to the code.
    The code runs inside of a docker container and uses uv package manager to quickly install the dependencies.

    Args:
        text (str): The Python code to execute.
        detect_packages (bool): Whether to detect the dependencies of the code.
    """
    if not is_program_installed("docker"):
        raise RuntimeError("Please install docker to use the execute function.")

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        file_path = temp_file.name
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

    if detect_packages:
        dependencies = _get_dependencies(text)
        with open(file_path, "r", encoding="utf-8") as f:
            script_content = f.read()

        new_content = (
            f"# /// script\n# dependencies = {json.dumps(dependencies.dependencies)}\n# ///\n"
            + script_content
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{file_path}:/usr/src/app/script.py:ro",
        "-w",
        "/usr/src/app",
        "ghcr.io/astral-sh/uv:0.5.4-python3.12-bookworm",
        "uv",
        "run",
        "script.py",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return res.stdout
