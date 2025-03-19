"""
MemberAccess class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class MemberAccess(Expression):
    def __init__(self, expr, member):
        self.expr = expr
        self.member = member

    def __str__(self):
        return (
            "MemberAccess(\n"
            + textwrap.indent(f"expr: {self.expr}\nmember: {self.member}", "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)