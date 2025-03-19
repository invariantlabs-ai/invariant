"""
ValueReference class for the IPL AST.
"""

from invariant.analyzer.language.ast.nodes.expression import Expression


class ValueReference(Expression):
    """
    A reference to a specific kind of value, e.g. <EMAIL_ADDRESS> or
    <PII>, as used in semantic patterns.
    """

    def __init__(self, value_type):
        self.value_type = value_type

    def __str__(self):
        return f"ValueReference({self.value_type})"

    def __repr__(self):
        return str(self)