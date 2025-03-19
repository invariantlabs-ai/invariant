"""
ObjectLiteral and ObjectEntry classes for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class ObjectLiteral(Expression):
    def __init__(self, entries):
        self.entries = entries

    def __str__(self):
        return (
            "ObjectLiteral(\n"
            + textwrap.indent("\n".join(str(entry) for entry in self.entries), "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)


class ObjectEntry(Expression):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __str__(self):
        return f"ObjectEntry({self.key}: {self.value})"

    def __repr__(self):
        return str(self)