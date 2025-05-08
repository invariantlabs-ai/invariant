"""
Relevant input objects for policy evaluation.

In a separate file, for better separation of dependencies.
"""

from typing import Optional, TypeVar

from invariant.analyzer.runtime.input import Input
from invariant.analyzer.runtime.symbol_table import SymbolTable
from invariant.analyzer.language.ast import Node

R = TypeVar("R")

class EvaluationContext:
    """
    An evaluation context enables a caller to handle the
    evaluation of external functions explicitly (e.g. for caching)
    and provide their own flow semantics (e.g. lookup in a graph).
    """

    def __init__(self, symbol_table: Optional[SymbolTable] = None):
        self.symbol_table = symbol_table

        self.evaluation_counter = 0

    def call_function(self, function, args, **kwargs):
        raise NotImplementedError("EvaluationContext must implement call_function()")

    async def acall_function(self, function, args, **kwargs):
        raise NotImplementedError("EvaluationContext must implement acall_function()")

    def link(self, function: R, node: Node | None) -> R:
        if self.symbol_table:
            return self.symbol_table.link(function, node)
        else:
            return function

    def has_flow(self, left, right):
        return False

    def is_parent(self, left, right):
        return False

    def get_policy_parameter(self, name):
        return None

    def has_policy_parameter(self, name):
        return False

    def get_input(self) -> Input:
        raise NotImplementedError("EvaluationContext must implement get_input()")


class PolicyParameters:
    """
    Returned when accessing `input` in the IPL, which provides access
    to policy parameters passed to the `.analyze(..., **kwargs)` function.
    """

    def __init__(self, context):
        self.context: EvaluationContext = context

    def get(self, key):
        return self.context.get_policy_parameter(key)

    def has_policy_parameter(self, key):
        return self.context.has_policy_parameter(key)
