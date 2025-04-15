"""
Semantic matching patterns as accessible in the IPA, e.g. (call is tool:func({x: "[0-9]+"})).
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from invariant.analyzer.language.ast import (
    ArrayLiteral,
    Node,
    NumberLiteral,
    ObjectLiteral,
    PolicyRoot,
    SemanticPattern,
    StringLiteral,
    ToolReference,
    Transformation,
    ValueReference,
    Wildcard,
)
from invariant.analyzer.runtime.nodes import text
from invariant.analyzer.stdlib.invariant.detectors import pii
from invariant.analyzer.stdlib.invariant.detectors.moderation import moderated
from invariant.analyzer.stdlib.invariant.nodes import ToolCall, ToolOutput


class SemanticPatternMatcher(ABC):
    """Matches a variable that is the result of a function call, where the function name matches the given pattern."""

    @staticmethod
    def from_semantic_pattern(pattern: SemanticPattern | ToolReference):
        if type(pattern) is ToolReference:
            return ToolCallMatcher(pattern.name, [])

        # determine type of top-level pattern
        return MatcherFactory().transform(pattern)

    @abstractmethod
    async def match(self, obj) -> bool:
        raise NotImplementedError


class MatcherFactory(Transformation):
    """
    Creates the matcher object from a given semantic pattern (AST node).
    """

    def transform(self, pattern: SemanticPattern):
        return self.visit(pattern)

    def visit_SemanticPattern(self, node: SemanticPattern):
        return ToolCallMatcher(node.tool_ref.name, [self.visit(arg) for arg in node.args])

    def visit_ObjectLiteral(self, node: ObjectLiteral):
        return DictMatcher({entry.key: self.visit(entry.value) for entry in node.entries})

    def visit_ArrayLiteral(self, node: ArrayLiteral):
        return ListMatcher([self.visit(arg) for arg in node.elements])

    def visit_ValueReference(self, node: ValueReference):
        if node.value_type not in VALUE_MATCHERS:
            raise ValueError(f"Unsupported value type: {node.value_type}")
        return VALUE_MATCHERS[node.value_type](node.value_type)

    def visit_Wildcard(self, node: Wildcard):
        return WildcardMatcher()

    def visit_StringLiteral(self, node: StringLiteral):
        return ConstantMatcher(node.value)

    def visit_NumberLiteral(self, node: NumberLiteral):
        return ConstantMatcher(node.value)

    def visit(self, node: Node | Any | PolicyRoot):
        result = super().visit(node)

        if isinstance(result, Node):
            raise ValueError(f"Unsupported semantic pattern: {node}")

        return result


@dataclass
class ConstantMatcher(SemanticPatternMatcher):
    """
    Matches constant values.
    """

    value: Any

    def __repr__(self):
        if type(self.value) is str:
            return f'ConstantMatcher("{self.value}")'
        return f"ConstantMatcher({self.value})"

    async def match_regex(self, value) -> bool:
        if type(self.value) is not str:
            return False
        return any(re.match(self.value + "$", t, re.DOTALL) is not None for t in text(value))

    async def match(self, value) -> bool:
        if not issubclass(type(value), type(self.value)):
            return False
        joined_value = "".join(text(value))
        return self.value == value or self.value == joined_value or await self.match_regex(value)


@dataclass
class DictMatcher(SemanticPatternMatcher):
    """
    Matches dictionary values.
    """

    entries: Dict[str, Any]

    def __repr__(self):
        return "DictMatcher({" + ", ".join(f"{k}: {v}" for k, v in self.entries.items()) + "})"

    async def match(self, value) -> bool:
        if not hasattr(value, "__getitem__"):
            return False

        for key, matcher in self.entries.items():
            try:
                if type(value) is not dict:
                    return False
                key_var = value[key]
                if not await matcher.match(key_var):
                    return False
            except KeyError:
                return False
        return True


@dataclass
class ListMatcher(SemanticPatternMatcher):
    """
    Matches list values.
    """

    elements: List[Any]

    def __repr__(self):
        return f"[{', '.join(map(str, self.elements))}]"

    async def match(self, value) -> bool:
        if type(value) is not list:
            return False
        if len(value) != len(self.elements):
            return False
        return all([await matcher.match(var) for matcher, var in zip(self.elements, value)])


@dataclass
class ToolCallMatcher(SemanticPatternMatcher):
    """
    Matches tool calls.
    """

    tool_pattern: str
    args: Optional[List[Any]]

    async def match(self, value) -> bool:
        if type(value) is ToolOutput and value._tool_call is not None:
            value = value._tool_call
        if type(value) is not ToolCall:
            return
        if not re.match(self.tool_pattern + "$", value.function.name):
            return False

        # for now, we only support keyword-based arguments (first positional argument is object of key-value pairs)
        if len(self.args) == 0:
            return True
        elif not len(self.args) == 1:
            return False

        return await self.args[0].match(value.function.arguments)

    def __repr__(self):
        return f"ToolCallMatcher({self.tool_pattern}, {self.args})"


@dataclass
class WildcardMatcher(SemanticPatternMatcher):
    """
    Matches any value.
    """

    pass

    def __repr__(self):
        return "*"

    async def match(self, value) -> bool:
        return True


VALUE_MATCHERS = {}


def value_matcher(cls):
    """
    Matches custom value types (e.g. PII, moderation categories).
    """
    # get supported value types from class
    supported_types = cls.SUPPORTED_TYPES
    for value_type in supported_types:
        VALUE_MATCHERS[value_type] = cls
    return cls


@value_matcher
@dataclass
class PIIMatcher(SemanticPatternMatcher):
    SUPPORTED_TYPES = ["EMAIL_ADDRESS", "LOCATION", "PHONE_NUMBER", "PERSON"]

    def __init__(self, entity: str):
        self.entity = entity

    def __repr__(self):
        return f"PIIMatcher({self.entity})"

    async def match(self, value) -> bool:
        from invariant.analyzer.runtime.evaluation import Interpreter

        result = await Interpreter.current().acall_function(pii, value)
        return self.entity in result


@value_matcher
@dataclass
class ModerationMatcher(SemanticPatternMatcher):
    SUPPORTED_TYPES = ["MODERATED"]

    def __init__(self, category: str):
        if category not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported moderation category: {category}")
        self.category = category

    def __repr__(self):
        return f"ModerationMatcher({self.category})"

    async def match(self, value) -> bool:
        from invariant.analyzer.runtime.evaluation import Interpreter

        return await Interpreter.current().acall_function(moderated, value)


ModerationMatcher.moderation_analyzer = None


@value_matcher
@dataclass
class ValueMatcherDummyMatcher(SemanticPatternMatcher):
    """
    Value matcher for <DUMMY> values.

    Only used in testing, to test the integration of custom value matchers,
    without having to rely on external libraries.
    """

    SUPPORTED_TYPES = ["DUMMY"]

    def __init__(self, entity: str):
        self.entity = entity

    def __repr__(self):
        return f"ValueMatcherDummyMatcher({self.entity})"

    async def match(self, value) -> bool:
        return value == "__DUMMY__"
