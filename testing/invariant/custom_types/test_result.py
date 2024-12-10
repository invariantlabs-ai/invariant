"""Describes the result class for the invariant runner."""

from invariant.custom_types.assertion_result import AssertionResult
from invariant.custom_types.trace import Trace
from pydantic import BaseModel


class TestResult(BaseModel):
    """Result of a test run."""

    name: str
    trace: Trace
    passed: bool
    assertions: list[AssertionResult]
    explorer_url: str
