"""
BooleanLiteral class for the IPL AST.
"""

from invariant.analyzer.language.ast.nodes.expression import Expression


class BooleanLiteral(Expression):
    def __init__(self, value):
        self.value = value
        self.type = bool

    def __str__(self):
        return f"BooleanLiteral({self.value})"

    def __repr__(self):
        return str(self)