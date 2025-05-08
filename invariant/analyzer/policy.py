import asyncio
import os
from typing import List, Optional, Tuple

from invariant.analyzer.base_policy import BasePolicy
from invariant.analyzer.language.ast import PolicyError, PolicyRoot
from invariant.analyzer.language.parser import parse, parse_file
from invariant.analyzer.runtime.evaluation import EvaluationResult
from invariant.analyzer.runtime.function_cache import FunctionCache
from invariant.analyzer.runtime.rule import Input, RuleSet
from invariant.analyzer.runtime.symbol_table import SymbolTable
from invariant.analyzer.stdlib.invariant.errors import (
    AnalysisResult,
    ErrorInformation,
    PolicyLoadingError,
    UnhandledError,
)
from invariant.analyzer.stdlib.invariant.nodes import Event

from .remote_policy import RemotePolicy


class LocalPolicy(BasePolicy):
    """
    A policy is a set of rules that are applied to an application state.

    Usage:

    ```python
    # from file
    policy = Policy.from_file("path/to/policy.iv")
    # from string
    policy = Policy.from_string(
    """

    ...
    """)
    ```

    Use `analyze` to apply the policy to an application state and to obtain a list of violations.
    """
    policy_root: PolicyRoot
    rule_set: RuleSet
    cached: bool

    def __init__(
        self, policy_root: PolicyRoot, cached=False, symbol_table: Optional[SymbolTable] = None
    ):
        """Creates a new policy with the given policy source.

        Args:
            policy_root: The root of the policy AST.
            cached: Whether to cache the triggerering of rules. Ensure that a rule only triggers once per
                    input, even across multiple calls to `analyze`. (default: False, relevant mostly for `Monitor`s)

        Raises:
            ValueError: If the policy source contains errors.
        """
        self.policy_root = policy_root
        if not (policy_root and len(policy_root.errors) == 0):
            msg = f"Failed to create policy from policy source. The following errors were found:\n{PolicyError.error_report(policy_root.errors)}"
            raise PolicyLoadingError(msg, policy_root.errors)
        self.rule_set = RuleSet.from_policy(
            policy_root, cached=cached, symbol_table=symbol_table or SymbolTable()
        )
        self.cached = cached

    @property
    def errors(self):
        return self.policy_root.errors

    @classmethod
    def from_file(cls, path: str) -> "LocalPolicy":
        return cls(parse_file(path))

    @classmethod
    def from_string(
        cls,
        string: str,
        path: str | None = None,
        optimize: bool = False,
        symbol_table: Optional[SymbolTable] = None,
    ) -> "LocalPolicy":
        return cls(parse(string, path, optimize_rules=optimize), symbol_table=symbol_table)

    def add_error_to_result(self, error, analysis_result: AnalysisResult):
        """Implements how errors are added to an analysis result (e.g. as handled or non-handled errors)."""
        analysis_result.errors.append(error)

    def analyze(self, input: list[dict], raise_unhandled=False, **policy_parameters):
        return asyncio.run(self.a_analyze(input, raise_unhandled, **policy_parameters))

    async def a_analyze(
        self,
        input: list[dict],
        raise_unhandled=False,
        function_cache: Optional[FunctionCache] = None,
        **policy_parameters,
    ):
        input = Input(input)

        # prepare policy parameters
        if "data" in policy_parameters:
            raise ValueError(
                "cannot use 'data' as policy parameter key, as it is reserved for the main input object"
            )
        # also make main input object available as policy parameter
        policy_parameters["data"] = input

        # apply policy rules
        rule_set = self.rule_set
        # use rule_set with provided cache
        rule_set = rule_set.instance(cache=function_cache)

        # evaluate rules
        exceptions: List[Tuple[EvaluationResult, ErrorInformation]] = await rule_set.apply(
            input, policy_parameters
        )

        # collect errors into result
        analysis_result = AnalysisResult(errors=[], handled_errors=[])
        for _, error in exceptions:
            self.add_error_to_result(error, analysis_result)

        if raise_unhandled and len(analysis_result.errors) > 0:
            raise UnhandledError(analysis_result.errors)

        return analysis_result

    def analyze_pending(
        self,
        past_events: list[dict],
        pending_events: list[dict],
        raise_unhandled=False,
        **policy_parameters,
    ):
        return asyncio.run(
            self.a_analyze_pending(
                past_events, pending_events, raise_unhandled, **policy_parameters
            )
        )

    async def a_analyze_pending(
        self,
        past_events: list[dict],
        pending_events: list[dict],
        raise_unhandled=False,
        **policy_parameters,
    ):
        first_pending_idx = len(past_events)
        input = Input(past_events + pending_events)

        # prepare policy parameters
        if "data" in policy_parameters:
            raise ValueError(
                "cannot use 'data' as policy parameter key, as it is reserved for the main input object"
            )
        # also make main input object available as policy parameter
        policy_parameters["data"] = input

        # apply policy rules
        self.rule_set.cached = self.cached
        exceptions = await self.rule_set.apply(input, policy_parameters)

        # collect errors into result
        analysis_result = AnalysisResult(errors=[])
        for model, error in exceptions:
            has_pending = False
            for val in model.variable_assignments.values():
                if (
                    isinstance(val, Event)
                    and val.metadata.get("trace_idx", -1) >= first_pending_idx
                ):
                    has_pending = True
            if has_pending:
                self.add_error_to_result(error, analysis_result)

        if raise_unhandled and len(analysis_result.errors) > 0:
            raise UnhandledError(analysis_result.errors)

        return analysis_result


def analyze_trace(policy_str: str, trace: list):
    policy = Policy.from_string(policy_str)
    return policy.analyze(trace)


Policy = LocalPolicy if os.getenv("LOCAL_POLICY", "0") == "1" else RemotePolicy
# in pytest run with (setting the env)
# pytest -o addopts='--env LOCAL_POLICY=1'
