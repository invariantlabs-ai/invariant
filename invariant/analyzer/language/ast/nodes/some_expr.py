"""
SomeExpr class for the IPL AST.
"""

import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class SomeExpr(Expression):
    """
    Non-deterministically chooses one of the elements of the list-like
    'candidates' expression. Used to represent the value of 'var' in the
    following snippet:

    ```
    raise "Invalid value" if:
        (var: type) in candidates
    ```
    """

    def __init__(self, candidates):
        self.candidates = candidates

    def __str__(self):
        return "SomeExpr(\n" + textwrap.indent(f"candidates: {self.candidates}", "  ") + "\n)"

    def __repr__(self):
        return str(self)