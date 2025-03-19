"""
Identifier and TypedIdentifier classes for the IPL AST.
"""

from invariant.analyzer.language.ast.nodes.expression import Expression


class Identifier(Expression):
    def __init__(self, name, namespace=None):
        self.name = name
        self.namespace = namespace
        # resolved after type checking
        self.id = None

    def __str__(self):
        suffix = ""

        if self.id is not None:
            suffix += f" (id: {self.id})"
        else:
            suffix += " (id: unresolved)"

        if self.namespace:
            return f"Identifier({self.namespace}:{self.name})" + suffix
        return f"Identifier({self.name})" + suffix

    def __repr__(self):
        return str(self)


class TypedIdentifier(Identifier):
    def __init__(self, type, name):
        super().__init__(name)
        self.type_ref = type

    def __str__(self):
        return f"TypedIdentifier({self.name}: {self.type_ref})"

    def __repr__(self):
        return str(self)