"""
ListComprehension class for the IPL AST.
"""

from invariant.analyzer.language.ast.nodes.lexical_scope_node import LexicalScopeNode


class ListComprehension(LexicalScopeNode):
    def __init__(self, expr, var_name, iterable, condition=None):
        super().__init__()
        self.expr = expr  # The expression to evaluate for each item
        self.var_name = var_name  # The variable name to use for iteration
        self.iterable = iterable  # The iterable to loop over
        self.condition = condition  # Optional filter condition

    def __str__(self):
        result = f"ListComprehension({self.expr} for {self.var_name} in {self.iterable}"
        if self.condition:
            result += f" if {self.condition}"
        result += ")"
        return result

    def __repr__(self):
        return str(self)