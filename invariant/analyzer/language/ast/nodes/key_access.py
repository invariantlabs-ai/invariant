"""
KeyAccess class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class KeyAccess(Expression):
    def __init__(self, expr, key):
        self.expr = expr
        self.key = key

    def __str__(self):
        return "KeyAccess(\n" + textwrap.indent(f"expr: {self.expr}\nkey: {self.key}", "  ") + ")"

    def __repr__(self):
        return str(self)