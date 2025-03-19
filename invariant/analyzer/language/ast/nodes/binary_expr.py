"""
BinaryExpr class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class BinaryExpr(Expression):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __str__(self):
        return (
            "BinaryExpr(\n"
            + textwrap.indent(f"  left: {self.left}\n  op: {self.op}\n  right: {self.right}", "  ")
            + "\n)"
        )

    def __repr__(self):
        return str(self)