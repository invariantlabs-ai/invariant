"""
ParameterDeclaration class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class ParameterDeclaration(Expression):
    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __str__(self):
        return (
            "ParameterDeclaration(\n"
            + textwrap.indent(f"name: {self.name}\ntype: {self.type}", "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)