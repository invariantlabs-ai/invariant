"""
Expression nodes for the IPL AST.
"""

from invariant.analyzer.language.ast.base import Node

class Expression(Node):
    def dependencies(self):
        # Import here to avoid circular import
        from invariant.analyzer.language.ast.transformations import FreeVarAnalysis
        return FreeVarAnalysis.get_free_vars(self)
