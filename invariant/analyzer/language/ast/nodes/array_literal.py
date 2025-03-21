"""
ArrayLiteral class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


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