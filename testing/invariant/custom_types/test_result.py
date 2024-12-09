"""Decribes the result class for the invariant runner."""

from pydantic import BaseModel

from invariant.custom_types.assertion_result import AssertionResult
from invariant.custom_types.trace import Trace


class TestResult(BaseModel):
    """Result of a test run."""

    name: str
    trace: Trace
    passed: bool
    assertions: list[AssertionResult]
    explorer_url: str
