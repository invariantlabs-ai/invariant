"""Describes an address range for characters in a text."""

from typing import Optional

from pydantic import BaseModel


class Range(BaseModel):
    """A character range in a text."""

    start: int
    end: int

    @staticmethod
    def from_line(text: str, line: int, exact_match: Optional[str] = None) -> "Range":
        """Create a character range corresponding to a line in a text."""
        lines = text.split("\n")
        if line >= len(lines):
            raise ValueError(
                f"Line number {line} is out of bounds for text with {len(lines)} lines"
            )

        if exact_match and exact_match in lines[line]:
            start = sum(len(line) + 1 for line in lines[:line]) + lines[line].index(
                exact_match
            )
            end = start + len(exact_match)
        else:
            start = sum(len(line) + 1 for line in lines[:line])
            end = start + len(lines[line])
        return Range(start=start, end=end)

    def to_address(self) -> str:
        """Convert the range to an address."""
        return str(self)

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"
