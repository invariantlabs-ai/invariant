"""
StringLiteral class for the IPL AST.
"""

import re
import textwrap
from invariant.analyzer.language.ast.nodes.expression import Expression


class StringLiteral(Expression):
    def __init__(self, value, multi_line=False, quote_type='"', modifier=None):
        self.type = str
        # for regex and format strings
        self.modifier = modifier  # e.g. 'r' or 'f'
        self.value = value

        if multi_line:
            self.value = textwrap.dedent(self.value)
        elif quote_type == '"':
            # replace '\"' with '"'
            self.value = re.sub(r"\\\"", '"', self.value)
        elif quote_type == "'":
            # replace "\'" with "'"
            self.value = re.sub(r"\\'", "'", self.value)

    def __str__(self):
        return f'StringLiteral("{self.value}")'

    def __repr__(self):
        return str(self)