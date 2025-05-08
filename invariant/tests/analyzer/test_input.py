import pytest

from invariant.analyzer import Policy
from invariant.analyzer.runtime.runtime_errors import InvariantInputValidationError


def test_invalid_input():
    data = [{"invalid-key": []}]
    policy = Policy.from_string("""raise "don\'t advertise inputSchema" if:
    (parameter: ToolParameter)
    print(parameter)""")

    with pytest.raises(InvariantInputValidationError) as excinfo:
        policy.analyze(data)


def test_valid_input():
    data = [{"tools": []}]
    policy = Policy.from_string("""raise "don\'t advertise inputSchema" if:
    (parameter: ToolParameter)
    print(parameter)""")

    try:
        policy.analyze(data)
    except InvariantInputValidationError as excinfo:
        assert False, f"Expected no error, but got: {excinfo.value}"
