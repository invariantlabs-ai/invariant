"""
Quantifier class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.base import Node


class Quantifier(Node):
    """
    Quantifiers like 'forall:\n    <expr>' or 'count(min=5):\n    <expr>'.
    """

    def __init__(self, quantifier_call, body):
        self.quantifier_call = quantifier_call
        self.body = body

    def __str__(self):
        return (
            "Quantifier(\n"
            + textwrap.indent(
                f"quantifier_call: {self.quantifier_call}\nbody:\n"
                + "\n".join(
                    "  " + str(stmt)
                    for stmt in (self.body if type(self.body) is list else [self.body])
                ),
                "  ",
            )
            + "\n)"
        )

    def __repr__(self):
        return str(self)