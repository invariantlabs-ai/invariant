"""Utility functions for the invariant runner."""

import ast
import json
import os
import shutil

from invariant.constants import (
    INVARIANT_AGENT_PARAMS_ENV_VAR,
    INVARIANT_RUNNER_TEST_RESULTS_DIR,
    INVARIANT_TEST_RUNNER_TERMINAL_WIDTH_ENV_VAR,
)


def get_agent_param(param: str) -> str | None:
    """Get a parameter from the environment variable."""
    params = os.getenv(INVARIANT_AGENT_PARAMS_ENV_VAR)
    if params is None:
        return None
    return json.loads(params)[param]


def get_test_results_directory_path(dataset_name: str) -> str:
    """Get the directory path for the test results."""
    return f"{INVARIANT_RUNNER_TEST_RESULTS_DIR}/results_for_{dataset_name}"


def ssl_verification_enabled():
    """Check if SSL verification is disabled."""
    return os.environ.get("SSL_VERIFY", "1") == "1"


def terminal_width():
    """Get the terminal width."""
    if INVARIANT_TEST_RUNNER_TERMINAL_WIDTH_ENV_VAR in os.environ:
        return int(os.environ[INVARIANT_TEST_RUNNER_TERMINAL_WIDTH_ENV_VAR])
    return shutil.get_terminal_size().columns


def ast_truncate(s: str, n: int = 256) -> str:
    """Smart truncation of python code snippets.

    Starting with the first line of the string, increasingly adds lines until the
    resulting string parses as a valid Python snippet. Returns the shortest such string that
    also contains at least one '(' character.

    This can be used to truncate a code snippet just to a single Python statement, even if
    assertions are formatted as multi-line code blocks.

    After this, the resulting string is unparsed to remove unnecessary whitespace and then
    truncated to the maximum length of `n` on a character level.

    Example:
    ```
    expect_equals(
        "123",
        trace.messages(1)['content']
    )
    # something else
    ```

    will be truncated to:

    ```
    expect_equals("123", trace.messages(1)['content'])
    ```
    """

    def check_string(s):
        # check if the string is a valid Python code snippet
        if "(" not in s:
            return False
        try:
            compile(s, "<string>", "exec")
            return True
        except SyntaxError as e:
            return False

    def postprocess(s: str):
        # parse and unparse to remove unnecessary whitespace
        tree = ast.parse(s)
        return ast.unparse(tree).strip()

    # add more lines until it parses
    lines = s.split("\n")
    for i in range(1, len(lines) + 1):
        if check_string("\n".join(lines[:i]).strip()):
            s = postprocess("\n".join(lines[:i]).strip())
            # also truncate to the maximum length
            return truncate(s, n=n)

    # otherwise returns the first line and truncate it to character length
    return truncate(lines[0].strip(), n=n)


def truncate(s: str, n: int) -> str:
    """Truncate a string to a maximum length."""
    return s[:n] + (s[n:] and "...")
