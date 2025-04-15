import os

import pytest

from invariant.analyzer import Policy
from invariant.analyzer.runtime.runtime_errors import (
    ExcessivePolicyError,
    InvariantAttributeError,
)
from invariant.analyzer.traces import system
from invariant.tests.analyzer.utils import user


@pytest.mark.parametrize(
    "method, expected_errors",
    [
        ("split", 1),
        ("strip", 1),
        ("lower", 1),
        ("upper", 1),
        ("splitlines", 1),
    ],
)
def test_string_and_dict_methods(method, expected_errors):
    policy_str = f"""
    raise PolicyViolation("some error") if:
        v := "abc"
        len(v.{method}()) > 0
    """
    policy = Policy.from_string(policy_str)
    trace = [
        system("You are a helpful assistant."),
        user("What is the result of something?"),
    ]
    result = policy.analyze(trace)
    assert (
        len(result.errors) == expected_errors
    ), f"Expected {expected_errors} errors, but got: {result.errors}"


@pytest.mark.parametrize(
    "method",
    [
        "replace",
        "keys",
        "values",
        "items",
        "get",
        "__dict__",  # Should not be allowed
    ],
)
def test_disallowed_methods_on_str(method):
    policy_str = f"""
    raise PolicyViolation("some error") if:
        v := "abc"
        len(v.{method}()) > 0
    """
    policy = Policy.from_string(policy_str)
    trace = [
        system("You are a helpful assistant."),
        user("What is the result of something?"),
    ]
    with pytest.raises(ExcessivePolicyError) as excinfo:
        result = policy.analyze(trace)
    assert f"Unavailable attribute {method}" in str(
        excinfo.value
    ), f"Expected ExcessivePolicyError for method {method}, but got: {excinfo.value}"


@pytest.mark.parametrize(
    "method, expected_errors",
    [
        ("keys", 1),
        ("values", 1),
        ("items", 1),
    ],
)
def test_allowed_methods_on_dict(method, expected_errors):
    policy_str = f"""
    raise PolicyViolation("some error") if:
        v := {{"key": "value"}}
        len(v.{method}()) > 0
    """
    policy = Policy.from_string(policy_str)
    trace = [
        system("You are a helpful assistant."),
        user("What is the result of something?"),
    ]
    result = policy.analyze(trace)
    assert (
        len(result.errors) == expected_errors
    ), f"Expected {expected_errors} errors, but got: {result.errors}"


def test_allowed_methods_on_dict_get_specifically():
    policy_str = """
    raise PolicyViolation("some error") if:
        v := {"key": "value"}
        v.get("key") == "value"
    """
    policy = Policy.from_string(policy_str)
    trace = [
        system("You are a helpful assistant."),
        user("What is the result of something?"),
    ]
    result = policy.analyze(trace)
    assert len(result.errors) == 1, f"Expected {1} errors, but got: {result.errors}"


@pytest.mark.parametrize(
    "method",
    [
        "update",
        "pop",
        "clear",
        "__dict__",  # Should not be allowed
    ],
)
def test_disallowed_methods_on_dict(method):
    policy_str = f"""
    raise PolicyViolation("some error") if:
        v := {{"key": "value"}}
        len(v.{method}()) > 0
    """
    policy = Policy.from_string(policy_str)
    trace = [
        system("You are a helpful assistant."),
        user("What is the result of something?"),
    ]
    with pytest.raises(ExcessivePolicyError) as excinfo:
        result = policy.analyze(trace)
    assert f"Unavailable attribute {method}" in str(
        excinfo.value
    ), f"Expected ExcessivePolicyError for method {method}, but got: {excinfo.value}"


@pytest.mark.parametrize(
    "attribute, valid",
    [
        ("role", True),
        ("content", True),
        ("tool_calls", True),
        ("metadata", True),
        ("invalid_attr", "not found"),  # Should not be allowed
        ("__dict__", "not found"),  # Should not be allowed
        ("__class__", "not found"),  # Should not be allowed
    ],
)
def test_allowed_attributes_on_message(attribute, valid):
    policy_str = f"""
    raise PolicyViolation("some error") if:
        (msg: Message)
        print(msg.{attribute})
    """
    policy = Policy.from_string(policy_str)
    trace = [
        user("What is the result of something?"),
    ]
    if valid is True:
        result = policy.analyze(trace)
        assert len(result.errors) == 1, f"Expected {1} errors, but got: {result.errors}"
    elif valid == "not found":
        with pytest.raises(InvariantAttributeError) as excinfo:
            result = policy.analyze(trace)
        assert "Invariant Attribute Error: Attribute" in str(
            excinfo.value
        ), f"Expected InvariantAttributeError for attribute {attribute}, but got: {excinfo.value}"
    else:
        with pytest.raises(ExcessivePolicyError) as excinfo:
            result = policy.analyze(trace)
        assert f"Unavailable attribute {attribute}" in str(
            excinfo.value
        ), f"Expected ExcessivePolicyError for attribute {attribute}, but got: {excinfo.value}"


def test_try_import_os():
    policy_str = """\
import os

raise PolicyViolation("some error") if:
    (msg: Message)
    os.path.exists("some_path") or os.system("uname -a") or True
"""
    policy = Policy.from_string(policy_str)
    trace = [
        system("You are a helpful assistant."),
        user("What is the result of something?"),
    ]

    # for 'LOCAL_POLICY' testing, we actually allow this (raw mode)
    if os.getenv("LOCAL_POLICY", "0") == "1":
        result = policy.analyze(trace)
        assert len(result.errors) == 1, f"Expected {1} errors, but got: {result.errors}"
    else:
        # otherwise, we do not allow this
        with pytest.raises(ExcessivePolicyError) as excinfo:
            result = policy.analyze(trace)


def test_try_import_json_loads():
    policy_str = """\
import json

raise PolicyViolation("some error") if:
    "key" in json.loads('{"key": "value"}')
"""

    policy = Policy.from_string(policy_str)

    trace = [
        system("You are a helpful assistant."),
        user("What is the result of something?"),
    ]

    result = policy.analyze(trace)

    assert len(result.errors) == 1, f"Expected {1} errors, but got: {result.errors}"
