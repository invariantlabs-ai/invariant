"""
Wildcard class for the IPL AST.
"""

from invariant.analyzer.language.ast.nodes.expression import Expression
from invariant.analyzer.language.types import UnknownType


class Wildcard(Expression):
    def __init__(self):
        self.type = UnknownType()

    def __str__(self):
        return "Wildcard()"

    def __repr__(self):
        return str(self)