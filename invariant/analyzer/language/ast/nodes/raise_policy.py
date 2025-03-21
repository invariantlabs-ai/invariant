"""
RaisePolicy class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.lexical_scope_node import LexicalScopeNode


class RaisePolicy(LexicalScopeNode):
    def __init__(self, exception_or_constructor, body):
        super().__init__()
        self.exception_or_constructor = exception_or_constructor
        self.body = body

    def __str__(self):
        return (
            "RaisePolicy(\n"
            + textwrap.indent(
                f"exception_or_constructor: {self.exception_or_constructor}\nbody:\n"
                + "\n".join("  " + str(stmt) for stmt in self.body),
                "  ",
            )
            + "\n)"
        )

    def __repr__(self):
        return str(self)
