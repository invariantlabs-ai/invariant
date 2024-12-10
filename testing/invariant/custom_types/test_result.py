"""Describes the result class for the invariant runner."""

from pydantic import BaseModel

from .assertion_result import AssertionResult
from .trace import Trace


class TestResult(BaseModel):
    """Result of a test run."""

    name: str
    trace: Trace
    passed: bool
    assertions: list[AssertionResult]
    explorer_url: str
