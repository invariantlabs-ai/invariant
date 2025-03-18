"""
Invariant Policy Language AST nodes.

This package provides the Abstract Syntax Tree nodes used to represent
the Invariant Policy Language (IPL) in memory.
"""

# Import components from submodules
from invariant.analyzer.language.ast.base import Node, Location, SourceCode
from invariant.analyzer.language.ast.errors import PolicyError
from invariant.analyzer.language.ast.expressions import (
    Expression, BinaryExpr, UnaryExpr, MemberAccess, KeyAccess,
    FunctionCall, FunctionSignature, ParameterDeclaration,
    Identifier, TypedIdentifier, ValueReference, SomeExpr,
    Import, ImportSpecifier
)
from invariant.analyzer.language.ast.literals import (
    StringLiteral, NumberLiteral, BooleanLiteral, NoneLiteral,
    ObjectLiteral, ObjectEntry, ArrayLiteral, ListComprehension,
    Wildcard
)
from invariant.analyzer.language.ast.statements import (
    LexicalScopeNode, PolicyRoot, RaisePolicy, Declaration,
    FunctionDefinition, Quantifier, SemanticPattern, ToolReference
)
from invariant.analyzer.language.ast.transformations import (
    Transformation, RaisingTransformation, Visitor,
    FreeVarAnalysis, CapturedVariableCollector, TransformationContext,
    TRANSFORMATION_CONTEXT_VAR
)

# For backward compatibility, re-export everything
__all__ = [
    # base.py
    'Node', 'Location', 'SourceCode',

    # errors.py
    'PolicyError',

    # expressions.py
    'Expression', 'BinaryExpr', 'UnaryExpr', 'MemberAccess', 'KeyAccess',
    'FunctionCall', 'FunctionSignature', 'ParameterDeclaration',
    'Identifier', 'TypedIdentifier', 'ValueReference', 'SomeExpr',
    'Import', 'ImportSpecifier',

    # literals.py
    'StringLiteral', 'NumberLiteral', 'BooleanLiteral', 'NoneLiteral',
    'ObjectLiteral', 'ObjectEntry', 'ArrayLiteral', 'ListComprehension',
    'Wildcard',

    # statements.py
    'LexicalScopeNode', 'PolicyRoot', 'RaisePolicy', 'Declaration',
    'FunctionDefinition', 'Quantifier', 'SemanticPattern', 'ToolReference',

    # transformations.py
    'Transformation', 'RaisingTransformation', 'Visitor',
    'FreeVarAnalysis', 'CapturedVariableCollector', 'TransformationContext',
    'TRANSFORMATION_CONTEXT_VAR',
]