"""
FunctionDefinition class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.base import Node


class FunctionDefinition(Node):
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body

    def __str__(self):
        return (
            "FunctionDefinition(\n"
            + textwrap.indent(
                f"name: {self.name}\nparams: {self.params}\nbody:\n"
                + "\n".join("  " + str(stmt) for stmt in self.body),
                "  ",
            )
            + "\n)"
        )

    def __repr__(self):
        return str(self)