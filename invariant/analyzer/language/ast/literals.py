"""
Literal expression nodes for the IPL AST.
"""

import re
import textwrap

from invariant.analyzer.language.ast.expressions import Expression
from invariant.analyzer.language.ast.statements import LexicalScopeNode
from invariant.analyzer.language.types import NoneType, UnknownType


class StringLiteral(Expression):
    def __init__(self, value, multi_line=False, quote_type='"', modifier=None):
        self.type = str
        # for regex and format strings
        self.modifier = modifier  # e.g. 'r' or 'f'
        self.value = value

        if multi_line:
            self.value = textwrap.dedent(self.value)
        elif quote_type == '"':
            # replace '\"' with '"'
            self.value = re.sub(r"\\\"", '"', self.value)
        elif quote_type == "'":
            # replace "\'" with "'"
            self.value = re.sub(r"\\'", "'", self.value)

    def __str__(self):
        return f'StringLiteral("{self.value}")'

    def __repr__(self):
        return str(self)


class NumberLiteral(Expression):
    def __init__(self, value):
        self.value = value
        assert type(value) in [int, float]

    def __str__(self):
        return f"NumberLiteral({self.value})"

    def __repr__(self):
        return str(self)


class BooleanLiteral(Expression):
    def __init__(self, value):
        self.value = value
        self.type = bool

    def __str__(self):
        return f"BooleanLiteral({self.value})"

    def __repr__(self):
        return str(self)


class NoneLiteral(Expression):
    def __init__(self):
        self.type = NoneType()

    def __str__(self):
        return "NoneLiteral()"

    def __repr__(self):
        return str(self)


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


class ArrayLiteral(Expression):
    def __init__(self, elements):
        self.elements = elements

    def __str__(self):
        return (
            "ArrayLiteral(\n"
            + textwrap.indent("\n".join(str(elem) for elem in self.elements), "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)


class ListComprehension(LexicalScopeNode):
    def __init__(self, expr, var_name, iterable, condition=None):
        super().__init__()
        self.expr = expr  # The expression to evaluate for each item
        self.var_name = var_name  # The variable name to use for iteration
        self.iterable = iterable  # The iterable to loop over
        self.condition = condition  # Optional filter condition

    def __str__(self):
        result = f"ListComprehension({self.expr} for {self.var_name} in {self.iterable}"
        if self.condition:
            result += f" if {self.condition}"
        result += ")"
        return result

    def __repr__(self):
        return str(self)


class Wildcard(Expression):
    def __init__(self):
        self.type = UnknownType()

    def __str__(self):
        return "Wildcard()"

    def __repr__(self):
        return str(self)