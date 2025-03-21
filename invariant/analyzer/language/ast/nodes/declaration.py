"""
Declaration class for the IPL AST.
"""

from invariant.analyzer.language.ast.nodes.lexical_scope_node import LexicalScopeNode


class Declaration(LexicalScopeNode):
    def __init__(self, name, value):
        super().__init__()
        self.name = name
        self.value = value

    @property
    def is_constant(self):
        from invariant.analyzer.language.ast.nodes import Identifier
        return type(self.name) is Identifier

    def __str__(self):
        value_repr = (
            str(self.value).encode("unicode_escape").decode("utf-8")
            if self.value is not None
            else "<uninitialized>"
        )
        value_repr = (value_repr[:30] + "...") if len(value_repr) > 30 else value_repr
        return f"Declaration(name: {self.name}, value: {value_repr})"

    def __repr__(self):
        return str(self)