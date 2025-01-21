import textwrap
from dataclasses import dataclass

from pydantic import BaseModel

from invariant.analyzer.language.ast import PolicyError, PolicyRoot
from invariant.analyzer.language.parser import parse, parse_file
from invariant.analyzer.runtime.rule import Input, RuleSet
from invariant.analyzer.stdlib.invariant.errors import ErrorInformation
from invariant.analyzer.stdlib.invariant.nodes import Event


@dataclass
class UnhandledError(Exception):
    errors: list[PolicyError]

    def __str__(self):
        errors_noun = "errors" if len(self.errors) > 1 else "error"
        errors_list = "\n".join(
            [" - " + type(error).__name__ + ": " + str(error) for error in self.errors]
        )
        return f"A policy analysis resulted in {len(self.errors)} unhandled {errors_noun}:\n{errors_list}.\n"


class AnalysisResult(BaseModel):
    """
    Result of applying a policy to an application state.

    Includes all unresolved errors, as well as resolved (handled) errors
    with corresponding handler calls (run them to actually resolve
    them in the application state).
    """

    errors: list[ErrorInformation]
    handled_errors: list[ErrorInformation]

    def execute_handlers(self):
        for handled_error in self.handled_errors:
            handled_error.execute_handler()

    def __str__(self):
        width = 120

        errors_str = "\n".join(
            [
                f"{textwrap.indent(textwrap.fill(str(error), width=width), ' ' * 4)}"
                for error in self.errors
            ]
        )
        error_line = "  errors=[]" if len(self.errors) == 0 else f"  errors=[\n{errors_str}\n  ]"

        handled_errors_str = "\n".join(
            [
                f"{textwrap.indent(textwrap.fill(str(handled_error), width=width), ' ' * 4)}"
                for handled_error in self.handled_errors
            ]
        )
        handled_error_line = (
            "  handled_errors=[]"
            if len(self.handled_errors) == 0
            else f"  handled_errors=[\n{handled_errors_str}\n  ]"
        )

        return f"AnalysisResult(\n{error_line},\n{handled_error_line}\n)"

    def __repr__(self):
        return self.__str__()


@dataclass
class PolicyLoadingError(Exception):
    """
    This exception is raised when a policy could not be loaded due to errors in
    the policy source (parsing, scoping, typing, validation, etc.).
    """

    msg: str
    errors: list[PolicyError]

    def __str__(self):
        return self.msg


class Policy:
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

    def __init__(self, policy_root: PolicyRoot, cached=False):
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
        self.rule_set = RuleSet.from_policy(policy_root, cached=cached)
        self.cached = cached

    @property
    def errors(self):
        return self.policy_root.errors

    @classmethod
    def from_file(cls, path: str) -> "Policy":
        return cls(parse_file(path))

    @classmethod
    def from_string(cls, string: str, path: str | None = None) -> "Policy":
        return cls(parse(string, path))

    def add_error_to_result(self, error, analysis_result):
        """Implements how errors are added to an analysis result (e.g. as handled or non-handled errors)."""
        analysis_result.errors.append(error)

    def analyze(self, input: list[dict], raise_unhandled=False, **policy_parameters):
        input = Input(input)

        # prepare policy parameters
        if "data" in policy_parameters:
            raise ValueError(
                "cannot use 'data' as policy parameter key, as it is reserved for the main input object"
            )
        # also make main input object available as policy parameter
        policy_parameters["data"] = input

        # apply policy rules
        exceptions = self.rule_set.apply(input, policy_parameters)

        # collect errors into result
        analysis_result = AnalysisResult(errors=[], handled_errors=[])
        for model, error in exceptions:
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
        exceptions = self.rule_set.apply(input, policy_parameters)

        # collect errors into result
        analysis_result = AnalysisResult(errors=[], handled_errors=[])
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
