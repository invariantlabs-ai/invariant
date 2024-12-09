"""Defines the Assertion class for test results."""

from typing import List, Literal

from pydantic import BaseModel


class AssertionResult(BaseModel):
    """Describes an assertion in a test."""

    passed: bool
    type: Literal["SOFT", "HARD"]
    addresses: List[str]
    message: str | None = None

    # snippet of the test code and offset of the
    # assertion in the test code snippet
    test: str | None = None
    test_line: int | None = None
