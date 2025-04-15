"""
Invariant Policy Language AST nodes.
"""

import asyncio
import contextvars
import io
import re
import sys
import textwrap
from typing import Any

import termcolor

from invariant.analyzer.language.scope import GlobalScope, Scope, VariableDeclaration  # noqa
from invariant.analyzer.language.types import NoneType, UnknownType


class PolicyError(ValueError):
    """
    If PolicyError is raised as part of a AST visitor, the resulting error message will be
    formatted as an issue with a policy file at the currently examined AST node (if available).
    """

    def __init__(self, message, node=None):
        super().__init__(message)
        # the associated AST node
        self.node: Node | None = node

    def as_dict(self):
        return {
            "message": str(self),
            "type": type(self).__name__,
            "line": self.node.location.line,
            "column": self.node.location.column,
            "path": self.node.location.code.path,
        }

    @staticmethod
    def to_dict(e: Exception):
        if isinstance(e, PolicyError):
            return e.as_dict()
        return {"message": str(e), "type": type(e).__name__}

    @staticmethod
    def error_report(errors: list[Exception]):
        output = io.StringIO()

        for error in errors:
            # handle 'PolicyError'
            if hasattr(error, "node") and error.node is not None:
                node: Node = error.node
                node.location.print_error(error, margin=1, output=output)
                output.write("\n")
            # handle other, e.g. lark parsing errors
            else:
                # Location.UNKNOWN.print_error(error, margin=1, output=output)
                output.write(str(error) + "\n")

        return output.getvalue()


class SourceCode:
    def __init__(self, code, path=None, verbose=False):
        self.path: str | None = path
        self.code: str = code
        self.verbose: bool = verbose

    def print_error(self, e, error_line, error_column, window=3, margin=0, output=None):
        if not self.verbose:
            return

        # by default, we print to stderr
        output = output or sys.stderr

        lines = self.code.split("\n")
        print("\n" * margin, end="", file=output)
        if self.path:
            print(termcolor.colored(f"File {self.path}:{error_line + 1}", "green"), file=output)
        for i in range(error_line - window, error_line + window + 1):
            if i == error_line:
                print(
                    termcolor.colored(
                        f"{i + 1:3}{'*' if i == error_line else ' '} | {lines[i]}", "red"
                    ),
                    file=output,
                )
                termcolor.cprint("     | " + " " * (error_column - 1) + "^", "yellow", file=output)
                termcolor.cprint(
                    "     | " + "\n".join(str(e).split("\n")[0:]), "yellow", file=output
                )
            elif i >= 0 and i < len(lines):
                print(f"{i + 1:3}  | {lines[i]}", file=output)
        print("\n" * margin, end="", file=output)

    def get_line(self, location):
        return self.code.split("\n")[location.line][location.column - 1 :]


class Location:
    def __init__(self, line, column, code):
        self.line = line
        self.column = column
        self.code: SourceCode = code

    def __str__(self):
        return f"Location(line: {self.line}, column: {self.column})"

    def __repr__(self):
        return str(self)

    def print_error(self, e, window=3, margin=0, output=None):
        if not self.code:
            print(str(e), "(cannot localize error, no source document set)")
            return
        self.code.print_error(
            e, self.line, self.column, window=window, margin=margin, output=output
        )

    @classmethod
    def from_items(cls, items, mappings, code):
        if len(items) > 0 and isinstance(items[0], Node):
            return items[0].location
        try:
            item_line, item_column = items.line, items.column
            item_line, char = mappings.get(items.line, (0, 0))
            # item_column += char - 1
            return cls(item_line, item_column, code)
        except AttributeError:
            return cls.UNKNOWN


Location.UNKNOWN = Location(-1, -1, None)


class Node:
    location: Location = Location.UNKNOWN
    type: Any = None

    def with_location(self, location):
        self.location = location
        return self


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
        self.source_code: SourceCode = None

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


class Expression(Node):
    def dependencies(self):
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


class NumberLiteral(Expression):
    def __init__(self, value):
        self.value = value
        assert type(value) in [int, float]

    def __str__(self):
        return f"NumberLiteral({self.value})"

    def __repr__(self):
        return str(self)


class BooleanLiteral(Expression):
    def __init__(self, value):
        self.value = value
        self.type = bool

    def __str__(self):
        return f"BooleanLiteral({self.value})"

    def __repr__(self):
        return str(self)


class ObjectLiteral(Expression):
    def __init__(self, entries):
        self.entries = entries

    def __str__(self):
        return (
            "ObjectLiteral(\n"
            + textwrap.indent("\n".join(str(entry) for entry in self.entries), "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)


class ObjectEntry(Expression):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __str__(self):
        return f"ObjectEntry({self.key}: {self.value})"

    def __repr__(self):
        return str(self)


class ArrayLiteral(Expression):
    def __init__(self, elements):
        self.elements = elements

    def __str__(self):
        return (
            "ArrayLiteral(\n"
            + textwrap.indent("\n".join(str(elem) for elem in self.elements), "  ")
            + ")"
        )

    def __repr__(self):
        return str(self)


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


class TernaryOp(Expression):
    def __init__(self, then_expr, condition, else_expr):
        self.then_expr = then_expr
        self.condition = condition
        self.else_expr = else_expr

    def __str__(self):
        return (
            "TernaryOp(\n"
            + textwrap.indent(f"  then_expr: {self.then_expr}\n  condition: {self.condition}\n  else_expr: {self.else_expr}", "  ")
            + "\n)"
        )

    def __repr__(self):
        return str(self)


class Identifier(Expression):
    def __init__(self, name, namespace=None):
        self.name = name
        self.namespace = namespace
        # resolved after type checking
        self.id: Declaration = None

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


class NoneLiteral(Expression):
    def __init__(self):
        self.type = NoneType()

    def __str__(self):
        return "NoneLiteral()"

    def __repr__(self):
        return str(self)


class Wildcard(Expression):
    def __init__(self):
        self.type = UnknownType()

    def __str__(self):
        return "Wildcard()"

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


class ToolReference(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"ToolReference(tool:{self.name})"

    def __repr__(self):
        return str(self)


class SemanticPattern(Expression):
    def __init__(self, tool_ref: ToolReference, args: list[Expression]):
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


TRANSFORMATION_CONTEXT_VAR = contextvars.ContextVar("transformation_context", default=[])


class TransformationContext:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        TRANSFORMATION_CONTEXT_VAR.get().append(self.value)

    def __exit__(self, exc_type, exc_value, traceback):
        TRANSFORMATION_CONTEXT_VAR.get().pop()

    @staticmethod
    def current():
        return TRANSFORMATION_CONTEXT_VAR.get()[-1]


class Transformation:
    def __init__(self, global_scope=None):
        self.global_scope = global_scope

    @property
    def context(self) -> Node | Any | LexicalScopeNode:
        return TransformationContext.current()

    def context_stack(self):
        return TRANSFORMATION_CONTEXT_VAR.get()

    def has_context(self, condition):
        for ctx in self.context_stack():
            if condition(ctx):
                return True
        return False

    def visit(self, node: (Node | Any | PolicyRoot)):
        if isinstance(node, PolicyRoot):
            return self.visit_PolicyRoot(node)
        elif isinstance(node, list):
            return [self.visit(x) for x in node]

        if isinstance(node, Node):
            method = "visit_" + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            return visitor(node)
        else:
            return node

    def generic_visit(self, node: Node):
        if isinstance(node, list):
            return [self.visit(x) for x in node]
        elif not isinstance(node, Node):
            return node
        else:
            for attr, value in node.__dict__.items():
                if attr in ["type", "parent"]:
                    continue
                setattr(node, attr, self.visit(value))
            return node

    def visit_PolicyRoot(self, node: PolicyRoot):
        with TransformationContext(node):
            node.statements = self.visit(node.statements)
        return node

    def visit_FunctionDefinition(self, node: FunctionDefinition):
        return self.generic_visit(node)

    def visit_Declaration(self, node: Declaration):
        return self.generic_visit(node)

    def visit_RaisePolicy(self, node: RaisePolicy):
        return self.generic_visit(node)

    def visit_Quantifier(self, node: Quantifier):
        return self.generic_visit(node)

    def visit_BinaryExpr(self, node: BinaryExpr):
        return self.generic_visit(node)

    def visit_UnaryExpr(self, node: UnaryExpr):
        return self.generic_visit(node)

    def visit_MemberAccess(self, node: MemberAccess):
        return self.generic_visit(node)

    def visit_FunctionCall(self, node: FunctionCall):
        return self.generic_visit(node)

    def visit_FunctionSignature(self, node: FunctionSignature):
        return self.generic_visit(node)

    def visit_ParameterDeclaration(self, node: ParameterDeclaration):
        return self.generic_visit(node)

    def visit_StringLiteral(self, node: StringLiteral):
        return self.generic_visit(node)

    def visit_Expression(self, node: Expression):
        return self.generic_visit(node)

    def visit_NumberLiteral(self, node: NumberLiteral):
        return self.generic_visit(node)

    def visit_Identifier(self, node: Identifier):
        return self.generic_visit(node)

    def visit_TypedIdentifier(self, node: TypedIdentifier):
        return self.generic_visit(node)

    def visit_ToolReference(self, node: ToolReference):
        return self.generic_visit(node)

    def visit_Import(self, node: Import):
        return self.generic_visit(node)

    def visit_ImportSpecifier(self, node: ImportSpecifier):
        return self.generic_visit(node)

    def visit_NoneLiteral(self, node: NoneLiteral):
        return self.generic_visit(node)

    def visit_BooleanLiteral(self, node: BooleanLiteral):
        return self.generic_visit(node)

    def visit_Wildcard(self, node: Wildcard):
        return self.generic_visit(node)

    def visit_SemanticPattern(self, node: SemanticPattern):
        return self.generic_visit(node)

    def visit_ObjectLiteral(self, node: ObjectLiteral):
        return self.generic_visit(node)

    def visit_ObjectEntry(self, node: ObjectEntry):
        return self.generic_visit(node)

    def visit_ArrayLiteral(self, node: ArrayLiteral):
        return self.generic_visit(node)
    
    def visit_ListComprehension(self, node: ListComprehension):
        return self.generic_visit(node)

    def visit_KeyAccess(self, node: KeyAccess):
        return self.generic_visit(node)

    def visit_ValueReference(self, node: ValueReference):
        return self.generic_visit(node)


class AsyncTransformation:
    def __init__(self, global_scope=None):
        self.global_scope = global_scope

    @property
    def context(self) -> Node | Any | LexicalScopeNode:
        return TransformationContext.current()

    def context_stack(self):
        return TRANSFORMATION_CONTEXT_VAR.get()

    def has_context(self, condition):
        for ctx in self.context_stack():
            if condition(ctx):
                return True
        return False

    async def visit(self, node: (Node | Any | PolicyRoot)):
        if isinstance(node, PolicyRoot):
            return await self.visit_PolicyRoot(node)
        elif isinstance(node, list):
            return await asyncio.gather(*[await self.visit(x) for x in node])

        if isinstance(node, Node):
            method = "visit_" + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            return await visitor(node)
        else:
            return node

    async def generic_visit(self, node: Node):
        if isinstance(node, list):
            return await asyncio.gather(*[self.visit(x) for x in node])
        elif not isinstance(node, Node):
            return node
        else:
            for attr, value in node.__dict__.items():
                if attr in ["type", "parent"]:
                    continue
                setattr(node, attr, await self.visit(value))
            return node

    async def visit_PolicyRoot(self, node: PolicyRoot):
        with TransformationContext(node):
            node.statements = await self.visit(node.statements)
        return node

    async def visit_FunctionDefinition(self, node: FunctionDefinition):
        return await self.generic_visit(node)

    async def visit_Declaration(self, node: Declaration):
        return await self.generic_visit(node)

    async def visit_RaisePolicy(self, node: RaisePolicy):
        return await self.generic_visit(node)

    async def visit_Quantifier(self, node: Quantifier):
        return await self.generic_visit(node)

    async def visit_BinaryExpr(self, node: BinaryExpr):
        return await self.generic_visit(node)

    async def visit_UnaryExpr(self, node: UnaryExpr):
        return await self.generic_visit(node)

    async def visit_MemberAccess(self, node: MemberAccess):
        return await self.generic_visit(node)

    async def visit_FunctionCall(self, node: FunctionCall):
        return await self.generic_visit(node)

    async def visit_FunctionSignature(self, node: FunctionSignature):
        return await self.generic_visit(node)

    async def visit_ParameterDeclaration(self, node: ParameterDeclaration):
        return await self.generic_visit(node)

    async def visit_StringLiteral(self, node: StringLiteral):
        return await self.generic_visit(node)

    async def visit_Expression(self, node: Expression):
        return await self.generic_visit(node)

    async def visit_NumberLiteral(self, node: NumberLiteral):
        return await self.generic_visit(node)

    async def visit_Identifier(self, node: Identifier):
        return await self.generic_visit(node)

    async def visit_TypedIdentifier(self, node: TypedIdentifier):
        return await self.generic_visit(node)

    async def visit_ToolReference(self, node: ToolReference):
        return await self.generic_visit(node)

    async def visit_Import(self, node: Import):
        return await self.generic_visit(node)

    async def visit_ImportSpecifier(self, node: ImportSpecifier):
        return await self.generic_visit(node)

    async def visit_NoneLiteral(self, node: NoneLiteral):
        return await self.generic_visit(node)

    async def visit_BooleanLiteral(self, node: BooleanLiteral):
        return await self.generic_visit(node)

    async def visit_Wildcard(self, node: Wildcard):
        return await self.generic_visit(node)

    async def visit_SemanticPattern(self, node: SemanticPattern):
        return await self.generic_visit(node)

    async def visit_ObjectLiteral(self, node: ObjectLiteral):
        return await self.generic_visit(node)

    async def visit_ObjectEntry(self, node: ObjectEntry):
        return await self.generic_visit(node)

    async def visit_ArrayLiteral(self, node: ArrayLiteral):
        return await self.generic_visit(node)

    async def visit_KeyAccess(self, node: KeyAccess):
        return await self.generic_visit(node)

    async def visit_ValueReference(self, node: ValueReference):
        return await self.generic_visit(node)


class RaisingTransformation(Transformation):
    """
    Transformation that prints source locations of PolicyErrors that occur
    during any visit method.

    Args:
        rereaise (bool, optional): If True, rereaises all PolicyErrors that occur during
            the transformation instead of re-raising them. Defaults to True.
    """

    def __init__(self, reraise=False, printing=True):
        super().__init__()
        self.errors = []
        self.reraise = reraise
        self.printing = printing

    def visit(self, node: Node | Any | PolicyRoot):
        try:
            return super().visit(node)
        except PolicyError as e:
            if hasattr(e, "node") and e.node is None:
                e.node = node
            self.errors.append(e)
            if self.reraise:
                raise e from None
        return node


class RaisingAsyncTransformation(AsyncTransformation):
    """
    Transformation that prints source locations of PolicyErrors that occur
    during any visit method.

    Args:
        rereaise (bool, optional): If True, rereaises all PolicyErrors that occur during
            the transformation instead of re-raising them. Defaults to True.
    """

    def __init__(self, reraise=False, printing=True):
        super().__init__()
        self.errors = []
        self.reraise = reraise
        self.printing = printing

    async def visit(self, node: Node | Any | PolicyRoot):
        try:
            return await super().visit(node)
        except PolicyError as e:
            if hasattr(e, "node") and e.node is None:
                e.node = node
            self.errors.append(e)
            if self.reraise:
                raise e from None
        return node


class Visitor(Transformation):
    def generic_visit(self, node: Node):
        if isinstance(node, list):
            return [self.visit(x) for x in node]
        elif not isinstance(node, Node):
            return node
        else:
            for attr, value in node.__dict__.items():
                if attr in ["type", "parent"]:
                    continue
                self.visit(value)
            return node


class FreeVarAnalysis(Visitor):
    def __init__(self):
        self.free_vars = []

    def visit_Identifier(self, node: Identifier):
        self.free_vars.append(node.name)
        return self.generic_visit(node)

    def visit_TypedIdentifier(self, node: TypedIdentifier):
        self.free_vars.append(node.name)
        return self.generic_visit(node)

    @staticmethod
    def get_free_vars(node):
        visitor = FreeVarAnalysis()
        visitor.visit(node)
        return visitor.free_vars


class CapturedVariableCollector(Visitor):
    """
    Collects all variables that are captured in a provided block or expression. More specifically, it collects all variables that are used but not declared in the provided block or expression, i.e. they are captured from the surrounding scope.

    Use .captured_variables() to get the set of captured variables.
    """

    def __init__(self):
        self.used_variables = set()
        self.declared_variables = set()

    def collect(self, expr):
        self.used_variables = set()
        self.declared_variables = set()
        self.visit(expr)
        return self.used_variables - self.declared_variables

    def visit_TypedIdentifier(self, node: TypedIdentifier):
        self.declared_variables.add(node.id)
        super().visit_TypedIdentifier(node)

    def visit_Identifier(self, node: Identifier):
        self.used_variables.add(node.id)
        super().visit_Identifier(node)
