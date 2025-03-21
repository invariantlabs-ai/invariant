"""
Import and ImportSpecifier classes for the IPL AST.
"""

from invariant.analyzer.language.ast.base import Node


class Import(Node):
    def __init__(self, module, import_specifiers, alias=None):
        self.module = module
        self.import_specifiers = import_specifiers
        self.alias = alias

    def __str__(self):
        if self.alias:
            return f"Import(module: {self.module}, import_specifiers: {self.import_specifiers}, alias: {self.alias})"
        return f"Import(module: {self.module}, import_specifiers: {self.import_specifiers})"

    def __repr__(self):
        return str(self)


class ImportSpecifier(Node):
    def __init__(self, name, alias=None):
        self.name = name
        self.alias = alias

    def __str__(self):
        if self.alias:
            return f"ImportSpecifier(name: {self.name}, alias: {self.alias})"
        return f"ImportSpecifier(name: {self.name})"

    def __repr__(self):
        return str(self)