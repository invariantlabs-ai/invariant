"""
Relevant input objects for policy evaluation.

In a separate file, for better separation of dependencies.
"""

from invariant.analyzer.runtime.input import Input


class EvaluationContext:
    """
    An evaluation context enables a caller to handle the
    evaluation of external functions explicitly (e.g. for caching)
    and provide their own flow semantics (e.g. lookup in a graph).
    """

    def call_function(self, function, args, **kwargs):
        return function(*args, **kwargs)

    def has_flow(self, left, right):
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
