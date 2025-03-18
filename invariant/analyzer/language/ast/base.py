"""
Base AST node classes and location information.
"""

import io
import sys
from typing import Any

import termcolor


class SourceCode:
    def __init__(self, code, path=None, verbose=False):
        self.path: str | None = path
        self.code: str = code
        self.verbose: bool = verbose

    def print_error(self, e, error_line, error_column, window=3, margin=0, output=None):
        if not self.verbose:
            return

        # by default, we print to stderr
        output = output or sys.stderr

        lines = self.code.split("\n")
        print("\n" * margin, end="", file=output)
        if self.path:
            print(termcolor.colored(f"File {self.path}:{error_line + 1}", "green"), file=output)
        for i in range(error_line - window, error_line + window + 1):
            if i == error_line:
                print(
                    termcolor.colored(
                        f"{i + 1:3}{'*' if i == error_line else ' '} | {lines[i]}", "red"
                    ),
                    file=output,
                )
                termcolor.cprint("     | " + " " * (error_column - 1) + "^", "yellow", file=output)
                termcolor.cprint(
                    "     | " + "\n".join(str(e).split("\n")[0:]), "yellow", file=output
                )
            elif i >= 0 and i < len(lines):
                print(f"{i + 1:3}  | {lines[i]}", file=output)
        print("\n" * margin, end="", file=output)

    def get_line(self, location):
        return self.code.split("\n")[location.line][location.column - 1 :]


class Location:
    def __init__(self, line, column, code):
        self.line = line
        self.column = column
        self.code: SourceCode = code

    def __str__(self):
        return f"Location(line: {self.line}, column: {self.column})"

    def __repr__(self):
        return str(self)

    def print_error(self, e, window=3, margin=0, output=None):
        if not self.code:
            print(str(e), "(cannot localize error, no source document set)")
            return
        self.code.print_error(
            e, self.line, self.column, window=window, margin=margin, output=output
        )

    @classmethod
    def from_items(cls, items, mappings, code):
        from invariant.analyzer.language.ast.base import Node

        if len(items) > 0 and isinstance(items[0], Node):
            return items[0].location
        try:
            item_line, item_column = items.line, items.column
            item_line, char = mappings.get(items.line, (0, 0))
            # item_column += char - 1
            return cls(item_line, item_column, code)
        except AttributeError:
            return cls.UNKNOWN


class Node:
    location: Location = None
    type: Any = None

    def with_location(self, location):
        self.location = location
        return self

# Set the UNKNOWN location
Location.UNKNOWN = Location(-1, -1, None)