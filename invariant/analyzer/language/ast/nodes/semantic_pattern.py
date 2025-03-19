"""
SemanticPattern and ToolReference classes for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class SemanticPattern(Expression):
    def __init__(self, tool_ref: 'ToolReference', args: list[Expression]):
        self.tool_ref = tool_ref
        self.args = args

    def __str__(self):
        return (
            "SemanticPattern(\n"
            + textwrap.indent(f"tool_ref: {self.tool_ref}\nargs: {self.args}", "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)


class ToolReference(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"ToolReference(tool:{self.name})"

    def __repr__(self):
        return str(self)