"""
TernaryOp class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class TernaryOp(Expression):
    def __init__(self, then_expr, condition, else_expr):
        self.then_expr = then_expr
        self.condition = condition
        self.else_expr = else_expr

    def __str__(self):
        return (
            "TernaryOp(\n"
            + textwrap.indent(f"  then_expr: {self.then_expr}\n  condition: {self.condition}\n  else_expr: {self.else_expr}", "  ")
            + "\n)"
        )

    def __repr__(self):
        return str(self)