"""
PolicyRoot class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.lexical_scope_node import LexicalScopeNode


class PolicyRoot(LexicalScopeNode):
    def __init__(self, statements):
        super().__init__()
        self.statements = statements

        # errors that occurred during typing or validation
        self.errors = []
        # source code document for error localization
        self.source_code = None

    def __str__(self):
        return (
            "Policy(\n"
            + textwrap.indent("\n".join(str(stmt) for stmt in self.statements), "  ")
            + "\n)"
        )

    def __repr__(self):
        return str(self)