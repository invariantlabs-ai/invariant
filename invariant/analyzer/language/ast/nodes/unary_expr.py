"""
UnaryExpr class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class UnaryExpr(Expression):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

    def __str__(self):
        return "UnaryExpr(\n" + textwrap.indent(f"op: {self.op}\nexpr: {self.expr}", "  ") + ")"

    def __repr__(self):
        return str(self)