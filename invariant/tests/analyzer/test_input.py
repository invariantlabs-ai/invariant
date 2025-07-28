import pytest
import json
from invariant.analyzer import Policy
from invariant.analyzer.runtime.runtime_errors import InvariantInputValidationError
from invariant.analyzer.runtime.rule import Input

QUERIES: list[bytes] = []
with open("invariant/tests/analyzer/sample_mcp_scan_request.jsonl", "rb") as f:
    for line in f:
        QUERIES.append(line)

@pytest.mark.parametrize(
    "idx, valid",
    [(idx, True) for idx in range(len(QUERIES))],
)
def test_input(idx: int, valid: bool):
    """
    Test the input validation of the policy.
    """
    input = json.loads(QUERIES[idx])
    if valid:
        try:
            Input(input)
        except InvariantInputValidationError as excinfo:
            assert False, f"Expected no error, but got: {excinfo}"
    else:
        with pytest.raises(InvariantInputValidationError):
            Input(input)
