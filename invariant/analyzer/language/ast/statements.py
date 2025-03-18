"""
Statement nodes for the IPL AST.
"""

import textwrap

from invariant.analyzer.language.ast.base import Node
from invariant.analyzer.language.ast.expressions import Expression
from invariant.analyzer.language.scope import Scope


class LexicalScopeNode(Node):
    """AST nodes that represent lexical scopes."""

    def __init__(self):
        self.scope = Scope()


class RaisePolicy(LexicalScopeNode):
    def __init__(self, exception_or_constructor, body):
        super().__init__()
        self.exception_or_constructor = exception_or_constructor
        self.body = body

    def __str__(self):
        return (
            "RaisePolicy(\n"
            + textwrap.indent(
                f"exception_or_constructor: {self.exception_or_constructor}\nbody:\n"
                + "\n".join("  " + str(stmt) for stmt in self.body),
                "  ",
            )
            + "\n)"
        )

    def __repr__(self):
        return str(self)


class Declaration(LexicalScopeNode):
    def __init__(self, name, value):
        super().__init__()
        self.name = name
        self.value = value

    @property
    def is_constant(self):
        from invariant.analyzer.language.ast.expressions import Identifier
        return type(self.name) is Identifier

    def __str__(self):
        value_repr = (
            str(self.value).encode("unicode_escape").decode("utf-8")
            if self.value is not None
            else "<uninitialized>"
        )
        value_repr = (value_repr[:30] + "...") if len(value_repr) > 30 else value_repr
        return f"Declaration(name: {self.name}, value: {value_repr})"

    def __repr__(self):
        return str(self)


class PolicyRoot(LexicalScopeNode):
    def __init__(self, statements):
        super().__init__()
        self.statements = statements

        # errors that occurred during typing or validation
        self.errors = []
        # source code document for error localization
        self.source_code = None

    def __str__(self):
        return (
            "Policy(\n"
            + textwrap.indent("\n".join(str(stmt) for stmt in self.statements), "  ")
            + "\n)"
        )

    def __repr__(self):
        return str(self)


class FunctionDefinition(Node):
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body

    def __str__(self):
        return (
            "FunctionDefinition(\n"
            + textwrap.indent(
                f"name: {self.name}\nparams: {self.params}\nbody:\n"
                + "\n".join("  " + str(stmt) for stmt in self.body),
                "  ",
            )
            + "\n)"
        )

    def __repr__(self):
        return str(self)


class Quantifier(Node):
    """
    Quantifiers like 'forall:\n    <expr>' or 'count(min=5):\n    <expr>'.
    """

    def __init__(self, quantifier_call, body):
        self.quantifier_call = quantifier_call
        self.body = body

    def __str__(self):
        return (
            "Quantifier(\n"
            + textwrap.indent(
                f"quantifier_call: {self.quantifier_call}\nbody:\n"
                + "\n".join(
                    "  " + str(stmt)
                    for stmt in (self.body if type(self.body) is list else [self.body])
                ),
                "  ",
            )
            + "\n)"
        )

    def __repr__(self):
        return str(self)


class SemanticPattern(Expression):
    def __init__(self, tool_ref: 'ToolReference', args: list[Expression]):
        self.tool_ref = tool_ref
        self.args = args

    def __str__(self):
        return (
            "SemanticPattern(\n"
            + textwrap.indent(f"tool_ref: {self.tool_ref}\nargs: {self.args}", "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)


class ToolReference(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"ToolReference(tool:{self.name})"

    def __repr__(self):
        return str(self)