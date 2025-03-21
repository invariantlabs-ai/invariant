"""
AST transformation and visitor machinery.
"""

import contextvars
from typing import Any

from invariant.analyzer.language.ast.base import Node
from invariant.analyzer.language.ast.errors import PolicyError
from invariant.analyzer.language.ast.nodes import PolicyRoot


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
    def context(self) -> Node | Any:
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

    def visit_FunctionDefinition(self, node):
        return self.generic_visit(node)

    def visit_Declaration(self, node):
        return self.generic_visit(node)

    def visit_RaisePolicy(self, node):
        return self.generic_visit(node)

    def visit_Quantifier(self, node):
        return self.generic_visit(node)

    def visit_BinaryExpr(self, node):
        return self.generic_visit(node)

    def visit_UnaryExpr(self, node):
        return self.generic_visit(node)

    def visit_MemberAccess(self, node):
        return self.generic_visit(node)

    def visit_FunctionCall(self, node):
        return self.generic_visit(node)

    def visit_FunctionSignature(self, node):
        return self.generic_visit(node)

    def visit_ParameterDeclaration(self, node):
        return self.generic_visit(node)

    def visit_StringLiteral(self, node):
        return self.generic_visit(node)

    def visit_Expression(self, node):
        return self.generic_visit(node)

    def visit_NumberLiteral(self, node):
        return self.generic_visit(node)

    def visit_Identifier(self, node):
        return self.generic_visit(node)

    def visit_TypedIdentifier(self, node):
        return self.generic_visit(node)

    def visit_ToolReference(self, node):
        return self.generic_visit(node)

    def visit_Import(self, node):
        return self.generic_visit(node)

    def visit_ImportSpecifier(self, node):
        return self.generic_visit(node)

    def visit_NoneLiteral(self, node):
        return self.generic_visit(node)

    def visit_BooleanLiteral(self, node):
        return self.generic_visit(node)

    def visit_Wildcard(self, node):
        return self.generic_visit(node)

    def visit_SemanticPattern(self, node):
        return self.generic_visit(node)

    def visit_ObjectLiteral(self, node):
        return self.generic_visit(node)

    def visit_ObjectEntry(self, node):
        return self.generic_visit(node)

    def visit_ArrayLiteral(self, node):
        return self.generic_visit(node)

    def visit_ListComprehension(self, node):
        return self.generic_visit(node)

    def visit_KeyAccess(self, node):
        return self.generic_visit(node)

    def visit_ValueReference(self, node):
        return self.generic_visit(node)


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

    def visit_Identifier(self, node):
        self.free_vars.append(node.name)
        return self.generic_visit(node)

    def visit_TypedIdentifier(self, node):
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

    def visit_TypedIdentifier(self, node):
        self.declared_variables.add(node.id)
        super().visit_TypedIdentifier(node)

    def visit_Identifier(self, node):
        self.used_variables.add(node.id)
        super().visit_Identifier(node)