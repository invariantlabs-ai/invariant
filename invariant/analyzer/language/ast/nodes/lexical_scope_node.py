"""
LexicalScopeNode base class for the IPL AST.
"""

from invariant.analyzer.language.ast.base import Node
from invariant.analyzer.language.scope import Scope


class LexicalScopeNode(Node):
    """AST nodes that represent lexical scopes."""

    def __init__(self):
        self.scope = Scope()