"""
Invariant Policy Language type system.
"""

from invariant.analyzer.language.ast import *
from invariant.analyzer.language.scope import ExternalReference, GlobalScope, VariableDeclaration
from invariant.analyzer.language.types import *


class CollectVariableDeclarations(RaisingTransformation):
    def __init__(self, scope) -> None:
        super().__init__()
        self.scope = scope
        self.declarations = []

    def visit_TypedIdentifier(self, node: TypedIdentifier):
        type_ref = node.type_ref
        declaration = self.scope.resolve(type_ref)
        if declaration is None:
            raise PolicyError(f"Failed to resolve type {type_ref}")
        ttype = NamedUnknownType(declaration.name)
        decl = VariableDeclaration(node.name, ttype)
        self.declarations.append(decl)
        node.id = decl
        return super().visit_TypedIdentifier(node)

    def visit_BinaryExpr(self, node: BinaryExpr):
        if node.op == ":=":
            self.declarations.append(VariableDeclaration(node.left.name, None, node.right))
        elif node.op == "in" and type(node.left) is TypedIdentifier:
            self.visit(node.right)
            type_ref = node.left.type_ref
            declaration = self.scope.resolve(type_ref)
            if declaration is None:
                raise PolicyError(f"Failed to resolve type {type_ref}")
            ttype = NamedUnknownType(declaration.name)
            decl = VariableDeclaration(node.left.name, ttype, SomeExpr(node.right))
            self.declarations.append(decl)
            node.left.id = decl
            return node

        return super().visit_BinaryExpr(node)


def declarations_to_dict(declarations):
    mapping = {}
    for decl in declarations:
        if decl.name in mapping:
            raise ValueError(f"Variable {decl.name} already declared")
        mapping[decl.name] = decl
    return mapping


class ImportScoping(Transformation):
    def __init__(self, global_scope) -> None:
        super().__init__()
        self.global_scope = global_scope

    def visit_Import(self, node: Import):
        if node.alias is not None:  # must be full import
            self.global_scope.declarations[node.alias] = VariableDeclaration(
                node.alias, UnknownType(), ExternalReference(node.module)
            )
        elif len(node.import_specifiers) == 0:
            self.global_scope.declarations[node.module] = VariableDeclaration(
                node.module, UnknownType(), ExternalReference(node.module)
            )
        else:
            for spec in node.import_specifiers:
                if spec.alias is not None:
                    self.global_scope.declarations[spec.alias] = VariableDeclaration(
                        spec.alias,
                        UnknownType(),
                        ExternalReference(node.module, spec.name),
                    )
                else:
                    self.global_scope.declarations[spec.name] = VariableDeclaration(
                        spec.name,
                        UnknownType(),
                        ExternalReference(node.module, spec.name),
                    )

        return node


class Scoping(RaisingTransformation):
    def __init__(self, global_scope) -> None:
        super().__init__()
        self.global_scope = global_scope

    def visit_PolicyRoot(self, node: PolicyRoot):
        top_level_declarations = []
        for stmt in node.statements:
            if isinstance(stmt, Declaration):
                top_level_declarations.append(VariableDeclaration.from_signature(stmt.name, stmt))
            elif isinstance(stmt, FunctionDefinition):
                top_level_declarations.append(VariableDeclaration.from_signature(stmt.name, stmt))
        node.scope.declarations = declarations_to_dict(top_level_declarations)
        node.scope.parent = self.global_scope
        node.scope.name = "policy"

        return super().visit_PolicyRoot(node)

    def visit_RaisePolicy(self, node: RaisePolicy):
        node.scope.parent = self.context.scope
        with TransformationContext(node):
            node.body, node.scope.declarations = self.visit_RuleBody(node.body)
            with TransformationContext(node):
                self.visit(node.exception_or_constructor)
        return node

    def visit_Declaration(self, node: Declaration):
        # check for predicate definition (with parameters as compared to constants)
        if isinstance(node.name, FunctionSignature):
            parameter_scope = Scope(
                parent=self.context.scope, name="parameters(" + str(node.name.name.name) + ")"
            )
            local_scope = Scope(
                parent=parameter_scope, name="locals(" + str(node.name.name.name) + ")"
            )
            node.scope = local_scope
            for p in node.name.params:
                decl = VariableDeclaration(p.name.name, parameter_scope.resolve_type(p.type))
                p.name.id = decl
                parameter_scope.declarations[p.name.name] = decl
        else:
            node.scope.parent = self.context.scope

        with TransformationContext(node):
            node.value, node.scope.declarations = self.visit_RuleBody(node.value)

        return node

    def visit_RuleBody(self, stmts: list[Node]):
        collector = CollectVariableDeclarations(self.global_scope)
        collector.visit(stmts)
        self.errors.extend(collector.errors)
        return stmts, declarations_to_dict(collector.declarations)


class TypingTransformation(RaisingTransformation):
    # BinaryExpr, UnaryExpr, MemberAccess, FunctionCall, FunctionSignature, ParameterDeclaration, StringLiteral, Identifier, NumberLiteral
    # RaisePolicy, Declaration, FunctionDefinition, Policy

    def visit_RaisePolicy(self, node: RaisePolicy):
        with TransformationContext(node):
            # first traverse body then exception_or_constructor
            node.body = [self.visit(stmt) for stmt in node.body]
            node.exception_or_constructor = self.visit(node.exception_or_constructor)
            return node

    def visit_MemberAccess(self, node: MemberAccess):
        node.expr = self.visit(node.expr)
        node.member = self.visit(node.member)

        # if we don't know the type of the expression, we can't type check the member access
        if isinstance(node.expr.type, UnknownType):
            node.type = UnknownType()
            return node

        node.type = UnknownType()

        return node

    def visit_SemanticPattern(self, node: SemanticPattern):
        with TransformationContext(node):
            return super().visit_SemanticPattern(node)

    def visit_Wildcard(self, node: Wildcard):
        if not self.has_context(lambda c: isinstance(c, SemanticPattern)):
            raise PolicyError(
                "You cannot use wildcards outside of semantic patterns (e.g. tool:abc(*, 12))"
            )
        return node

    def visit_ValueReference(self, node: ValueReference):
        from invariant.analyzer.runtime.patterns import VALUE_MATCHERS

        if not self.has_context(lambda c: isinstance(c, SemanticPattern)):
            raise PolicyError(
                "You cannot use value references outside of semantic patterns (e.g. tool:abc(<VALUE>, 12))"
            )
        if node.value_type not in VALUE_MATCHERS:
            raise PolicyError(
                f"Unsupported value type: {node.value_type}. Available types: {' '.join(VALUE_MATCHERS.keys())}"
            )

        return node

    def visit_KeyAccess(self, node: KeyAccess):
        node.key = self.visit(node.key)
        node.expr = self.visit(node.expr)

        node.type = UnknownType()

        return node

    def visit_Import(self, node: Import):
        return node

    def visit_Declaration(self, node: Declaration):
        with TransformationContext(node):
            node.value = self.visit(node.value)
            return node

    def visit_FunctionCall(self, node: FunctionCall):
        node.name = self.visit(node.name)
        node.args = [self.visit(arg) for arg in node.args]
        node.kwargs = [self.visit(entry) for entry in node.kwargs]
        # if we don't know the type of the function, we can't type check the arguments
        if node.name.type is None:
            return node
        function_type = node.name.type
        if isinstance(function_type, UnknownType):
            node.type = UnknownType()
            return node
        elif not isinstance(function_type, FunctionType):
            raise PolicyError(f"Expected function, got {function_type}")
        node.type = function_type.return_type
        return node

    def visit_Identifier(self, node: Identifier):
        # print("context", node, type(self.context), self.context.scope)
        declaration = self.context.scope.resolve(node.name)
        if declaration is None:
            raise PolicyError(f"Failed to resolve identifier {node.name}")
        node.type = declaration.type_ref
        node.id = declaration
        return node

    def visit_ListComprehension(self, node: ListComprehension):
        # First visit the iterable to ensure it's typed correctly
        node.iterable = self.visit(node.iterable)

        # Set up the scope for the iteration variable
        node.scope.parent = self.context.scope

        # Add the iteration variable to the scope
        var_name = node.var_name.name if hasattr(node.var_name, "name") else node.var_name
        var_decl = VariableDeclaration(var_name, UnknownType())
        node.scope.declarations = {var_name: var_decl}

        # Set the id on the var_name if it's an Identifier
        if isinstance(node.var_name, Identifier):
            node.var_name.id = var_decl

        # Now visit the expression with the iteration variable in scope
        with TransformationContext(node):
            node.expr = self.visit(node.expr)
            if node.condition:
                node.condition = self.visit(node.condition)

        # The type of the list comprehension is a list of the expression type
        node.type = UnknownType

        return node

    def visit_BinaryExpr(self, node: BinaryExpr):
        result = super().visit_BinaryExpr(node)
        return result


def typing(policy: PolicyRoot):
    # fresh scope for all imports in this policy file
    module_scope = Scope(parent=GlobalScope, name="global")
    ImportScoping(module_scope).visit(policy)
    scoping_transform = Scoping(module_scope)
    scoping_transform.visit(policy)
    # collect scoping errors
    policy.errors.extend(scoping_transform.errors)

    # type check the policy
    typing_transform = TypingTransformation()
    typing_transform.visit(policy)
    # collect typing errors
    policy.errors.extend(typing_transform.errors)

    return policy
