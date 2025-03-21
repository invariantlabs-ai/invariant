"""
FunctionSignature class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class FunctionSignature(Expression):
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __str__(self):
        return (
            "FunctionSignature(\n"
            + textwrap.indent(f"name: {self.name}\nparams: {self.params}", "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)