"""
NumberLiteral class for the IPL AST.
"""

from invariant.analyzer.language.ast.nodes.expression import Expression


class NumberLiteral(Expression):
    def __init__(self, value):
        self.value = value
        assert type(value) in [int, float]

    def __str__(self):
        return f"NumberLiteral({self.value})"

    def __repr__(self):
        return str(self)