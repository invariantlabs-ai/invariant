"""
FunctionCall class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression
from invariant.analyzer.language.ast.nodes.object_literal import ObjectEntry


class FunctionCall(Expression):
    def __init__(self, name, args):
        self.name = name
        self.args = [a for a in args if type(a) is not tuple]
        self.kwargs = [ObjectEntry(*entry) for entry in args if type(entry) is tuple]

    def __str__(self):
        return (
            "FunctionCall(\n"
            + textwrap.indent(f"name: {self.name}\nargs: {self.args}", "  ")
            + textwrap.indent(f"\nkwargs: {self.kwargs}", "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)