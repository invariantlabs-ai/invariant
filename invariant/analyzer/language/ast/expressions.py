"""
Expression nodes for the IPL AST.
"""

import textwrap
from typing import Any

from invariant.analyzer.language.ast.base import Node
from invariant.analyzer.language.types import NoneType, UnknownType


class Expression(Node):
    def dependencies(self):
        from invariant.analyzer.language.ast.transformations import FreeVarAnalysis
        return FreeVarAnalysis.get_free_vars(self)


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


class BinaryExpr(Expression):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __str__(self):
        return (
            "BinaryExpr(\n"
            + textwrap.indent(f"  left: {self.left}\n  op: {self.op}\n  right: {self.right}", "  ")
            + "\n)"
        )

    def __repr__(self):
        return str(self)


class UnaryExpr(Expression):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

    def __str__(self):
        return "UnaryExpr(\n" + textwrap.indent(f"op: {self.op}\nexpr: {self.expr}", "  ") + ")"

    def __repr__(self):
        return str(self)


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


class KeyAccess(Expression):
    def __init__(self, expr, key):
        self.expr = expr
        self.key = key

    def __str__(self):
        return "KeyAccess(\n" + textwrap.indent(f"expr: {self.expr}\nkey: {self.key}", "  ") + ")"

    def __repr__(self):
        return str(self)


class FunctionCall(Expression):
    def __init__(self, name, args):
        self.name = name
        self.args = [a for a in args if type(a) is not tuple]
        self.kwargs = [ObjectEntry(*entry) for entry in args if type(entry) is tuple]

    def __str__(self):
        return (
            "FunctionCall(\n"
            + textwrap.indent(f"name: {self.name}\nargs: {self.args}", "  ")
            + textwrap.indent(f"\nkwargs: {self.kwargs}", "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)


class FunctionSignature(Expression):
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __str__(self):
        return (
            "FunctionSignature(\n"
            + textwrap.indent(f"name: {self.name}\nparams: {self.params}", "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)


class ParameterDeclaration(Expression):
    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __str__(self):
        return (
            "ParameterDeclaration(\n"
            + textwrap.indent(f"name: {self.name}\ntype: {self.type}", "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)


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


class ValueReference(Expression):
    """
    A reference to a specific kind of value, e.g. <EMAIL_ADDRESS> or
    <PII>, as used in semantic patterns.
    """

    def __init__(self, value_type):
        self.value_type = value_type

    def __str__(self):
        return f"ValueReference({self.value_type})"

    def __repr__(self):
        return str(self)


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


# Circular import - need to set this relation here
from invariant.analyzer.language.ast.literals import ObjectEntry