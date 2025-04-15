from invariant.analyzer.language.ast import (
    ArrayLiteral,
    BinaryExpr,
    BooleanLiteral,
    Declaration,
    Expression,
    FunctionCall,
    FunctionDefinition,
    FunctionSignature,
    Identifier,
    Import,
    ImportSpecifier,
    KeyAccess,
    MemberAccess,
    Node,
    NoneLiteral,
    NumberLiteral,
    ObjectEntry,
    ObjectLiteral,
    ParameterDeclaration,
    PolicyRoot,
    Quantifier,
    RaisePolicy,
    SemanticPattern,
    StringLiteral,
    ToolReference,
    Transformation,
    TransformationContext,
    TypedIdentifier,
    UnaryExpr,
    ValueReference,
    Wildcard,
)


class CostEstimator(Transformation):
    def visit_PolicyRoot(self, node: PolicyRoot):
        with TransformationContext(node):
            node.statements = self.visit(node.statements)
        return node

    def generic_visit(self, node: Node):
        if isinstance(node, list):
            return max([self.visit(x) for x in node])
        elif not isinstance(node, Node):
            return node
        else:
            max_value = 0
            for attr, value in node.__dict__.items():
                if attr in ["type", "parent"]:
                    continue
                c = self.visit(value)
                if type(c) is float or type(c) is int:
                    max_value = max(max_value, c)
            return max_value

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
        if node.name == "prompt_injection":
            return 2.0
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

    def visit_KeyAccess(self, node: KeyAccess):
        return self.generic_visit(node)

    def visit_ValueReference(self, node: ValueReference):
        return self.generic_visit(node)


def optimize_RaisePolicy(raise_policy: RaisePolicy):
    # sort policy statements bodies by cost, so short-circuiting is more likely to be effective
    sorted_statements = sorted(raise_policy.body, key=lambda s: CostEstimator().visit(s))
    raise_policy.body = [s for s in sorted_statements]

    return raise_policy


def optimize(policy: PolicyRoot):
    for stmt in policy.statements:
        if type(stmt) is RaisePolicy:
            optimize_RaisePolicy(stmt)

    return policy
