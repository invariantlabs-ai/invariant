"""
Semantic matching patterns as accessible in the IPA, e.g. (call is tool:func({x: "[0-9]+"})).
"""
import re
from typing import Optional, List
from dataclasses import dataclass
from typing import List, Dict, Any
from invariant.language.ast import ArrayLiteral, Node, NumberLiteral, ObjectLiteral, PolicyRoot, SemanticPattern, StringLiteral, Transformation, Node, ToolReference, ValueReference, Wildcard

from abc import ABC, abstractmethod
from invariant.runtime.utils.pii import PII_Analyzer
from invariant.runtime.utils.moderation import ModerationAnalyzer
from invariant.stdlib.invariant.nodes import Message, ToolCall, ToolOutput

class SemanticPatternMatcher(ABC):
    """Matches a variable that is the result of a function call, where the function name matches the given pattern."""

    @staticmethod
    def from_semantic_pattern(pattern: SemanticPattern | ToolReference):
        if type(pattern) is ToolReference:
            return ToolCallMatcher(pattern.name, [])

        # determine type of top-level pattern
        return MatcherFactory().transform(pattern)

    @abstractmethod
    def match(self, obj) -> bool:
        raise NotImplementedError

class MatcherFactory(Transformation):
    """
    Creates the matcher object from a given semantic pattern (AST node).
    """
    def transform(self, pattern: SemanticPattern):
        return self.visit(pattern)
    
    def visit_SemanticPattern(self, node: SemanticPattern):
        return ToolCallMatcher(
            node.tool_ref.name,
            [self.visit(arg) for arg in node.args]
        )

    def visit_ObjectLiteral(self, node: ObjectLiteral):
        return DictMatcher({entry.key: self.visit(entry.value) for entry in node.entries})

    def visit_ArrayLiteral(self, node: ArrayLiteral):
        return ListMatcher([self.visit(arg) for arg in node.elements])

    def visit_ValueReference(self, node: ValueReference):
        if not node.value_type in VALUE_MATCHERS:
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

    def match_regex(self, value) -> bool:
        if type(self.value) is not str:
            return False
        return re.match(self.value + "$", value, re.DOTALL) is not None

    def match(self, value) -> bool:
        if not issubclass(type(value), type(self.value)):
            return False
        return self.value == value or self.match_regex(value)

@dataclass
class DictMatcher(SemanticPatternMatcher):
    """
    Matches dictionary values.
    """
    entries: Dict[str, Any]

    def __repr__(self):
        return "DictMatcher({" + ", ".join(f"{k}: {v}" for k, v in self.entries.items()) + "})"

    def match(self, value) -> bool:
        if not hasattr(value, "__getitem__"):
            return False

        for key, matcher in self.entries.items():
            try: 
                if not type(value) is dict:
                    return False
                key_var = value[key]
                if not matcher.match(key_var):
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
    
    def match(self, value) -> bool:
        if not type(value) is list:
            return False
        if len(value) != len(self.elements):
            return False
        return all(matcher.match(var) for matcher, var in zip(self.elements, value))

@dataclass
class ToolCallMatcher(SemanticPatternMatcher):
    """
    Matches tool calls.
    """
    tool_pattern: str
    args: Optional[List[Any]]

    def match(self, value) -> bool:
        if type(value) is ToolOutput and value._tool_call is not None:
            value = value._tool_call
        if not type(value) is ToolCall:
            return
        if not re.match(self.tool_pattern + "$", value.function.name):
            return False
        
        # for now, we only support keyword-based arguments (first positional argument is object of key-value pairs)
        if len(self.args) == 0:
            return True
        elif not len(self.args) == 1:
            return False

        return self.args[0].match(value.function.arguments)

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
    
    def match(self, value) -> bool:
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
    
    def match(self, value) -> bool:
        if not PIIMatcher.pii_analyzer:
            PIIMatcher.pii_analyzer = PII_Analyzer()
        pii_analyzer = PIIMatcher.pii_analyzer

        res = pii_analyzer.detect_all(value)
        res = [r.entity_type for r in res]

        return self.entity in res

PIIMatcher.pii_analyzer = None

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
    
    def match(self, value) -> bool:
        if not ModerationMatcher.moderation_analyzer:
            ModerationMatcher.moderation_analyzer = ModerationAnalyzer()
        moderation_analyzer = ModerationMatcher.moderation_analyzer

        if not type(value) is str:
            return False

        return moderation_analyzer.detect(value)
    
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
    
    def match(self, value) -> bool:
        return value == "__DUMMY__"
        