"""
NoneLiteral class for the IPL AST.
"""

from invariant.analyzer.language.ast.nodes.expression import Expression
from invariant.analyzer.language.types import NoneType


class NoneLiteral(Expression):
    def __init__(self):
        self.type = NoneType()

    def __str__(self):
        return "NoneLiteral()"

    def __repr__(self):
        return str(self)