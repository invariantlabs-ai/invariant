import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import partial

from invariant.analyzer.policy import (
    AnalysisResult,
    Input,
    Policy,
    UnhandledError,
    parse_file,
)
from invariant.analyzer.runtime.rule import RuleSet


class HandledError:
    """
    A handled error is an error that can be resolved by
    applying the associated handler.
    """

    def __init__(self, handler, error):
        self.handler = handler
        self.error = error

    def execute_handler(self):
        if is_wrapping(self.handler):
            return  # do not execute wrapping handlers here
        self.handler(self.error)

    def __str__(self):
        return f"HandledError(handler={self.handler}, error={self.error})"

    def __repr__(self):
        return self.__str__()


@dataclass
class OperationCall:
    args: list
    kwargs: dict


class ValidatedOperation(ABC):
    def __init__(self, call: OperationCall):
        self.call: OperationCall = call

    @abstractmethod
    def pre(self):
        """
        Prepares the operation and creates a corresponding call object in the application trace

        :return: The updated application trace.
        """
        raise NotImplementedError

    @abstractmethod
    def run(self):
        """Runs the operation and returns the output."""
        raise NotImplementedError

    @abstractmethod
    def post(self, result):
        """
        Finalizes the operation and integrates the result into the application trace.

        :param result: The updated application trace.
        """
        raise NotImplementedError


def is_wrapping(handler):
    parameters = inspect.signature(handler).parameters
    # is function with 'call', 'call_next' and 'error' arguments
    return "call_next" in parameters


class Monitor:
    """
    A monitor is a policy that can be incrementally applied to an application state.

    It can be used to check the application state for policy violations and to apply handlers to resolve them.

    Across the lifetime of a Monitor, errors are reported in an accumulating manner. This means across all calls
    to `check()`, an error relating to a specific part of the application state will only be reported once, even if
    it persists in the application state. This allows the client to handle or ignore errors as they see fit, without
    having to worry about duplicate error reports.
    """

    def __init__(self, policy: Policy, policy_parameters: dict, raise_unhandled=False):
        """Creates a new monitor with the given policy source.

        Args:
            policy_root: The root of the policy AST.

        Raises:
            ValueError: If the policy source contains errors.
        """
        # we are using an incremental policy here to enable stateful analysis (only show new error on each call)
        self.policy = policy.incremental()
        # policy parameters used in `check()` calls
        self.policy_parameters = policy_parameters
        # whether to raise unhandled errors in `check()`
        self.raise_unhandled = raise_unhandled or policy_parameters.pop("raise_unhandled", False)

    def reset(self):
        """Resets the monitor to its initial state (incremental state is cleared)."""
        self.rule_set = RuleSet.from_policy(self.policy_root, cached=self.cached)

    @classmethod
    def from_file(cls, path: str, **policy_parameters):
        return cls(parse_file(path), policy_parameters)

    @classmethod
    def from_string(
        cls,
        string: str,
        optimize: bool = False,
        symbol_table=None,
        **policy_parameters,
    ):
        return cls(
            Policy.from_string(string, optimize=optimize, symbol_table=symbol_table),
            policy_parameters,
        )

    def analyze(self, input: dict, raise_unhandled=False, **policy_parameters):
        return self.policy.analyze(input, raise_unhandled=raise_unhandled, **policy_parameters)

    def analyze_pending(
        self,
        past_events: list[dict],
        pending_events: list[dict],
        raise_unhandled=False,
        **policy_parameters,
    ):
        return self.policy.analyze_pending(
            past_events, pending_events, raise_unhandled=raise_unhandled, **policy_parameters
        )

    def check(self, past_events: list[dict], pending_events: list[dict]):
        analysis_result = self.policy.analyze_pending(
            past_events, pending_events, **self.policy_parameters
        )
        if self.raise_unhandled and len(analysis_result.errors) > 0:
            raise UnhandledError(analysis_result.errors)
        return analysis_result.errors

    def add_error_to_result(self, error, analysis_result):
        analysis_result.errors.append(error)

    def run(self, operation: ValidatedOperation):
        # prepare the operation and collect potential errors
        application_state = operation.pre()
        analysis_result = self.analyze(Input(application_state))
        # check for unhandled errors (i.e. errors that have no handler)
        if len(analysis_result.errors) > 0:
            raise UnhandledError(analysis_result.errors)
        wrappers = [
            partial(handler_call.handler, error=handler_call.error)
            for handler_call in analysis_result.handled_errors
            if is_wrapping(handler_call.handler)
        ]
        call_stack = stack(wrappers + [operation.run])

        result = call_stack(operation.call)

        # finalize the operation and collect potential errors
        application_state = operation.post(result)

        # apply the changes to the application state
        analysis_result = self.analyze(Input(application_state))
        # check for unhandled errors (i.e. errors that have no handler)
        if len(analysis_result.errors) > 0:
            raise UnhandledError(analysis_result.errors)

        return result

    def validated(self, application_state):
        def decorator(func):
            def wrapped_func(*args, **kwargs):
                class DecoratorBasedValidatedOperation(ValidatedOperation):
                    def __init__(self):
                        super().__init__(OperationCall(list(args), kwargs))

                        self.call_obj = {
                            "type": "ToolCall",
                            "tool": func.__name__,
                            "input": {"args": self.call.args, "kwargs": self.call.kwargs},
                            "output": None,
                        }

                    def pre(self):
                        application_state["messages"].append(self.call_obj)

                        return application_state

                    def run(self, call: OperationCall):
                        self.call_obj["input"] = {
                            "args": self.call.args,
                            "kwargs": self.call.kwargs,
                        }
                        return func(*call.args, **call.kwargs)

                    def post(self, result):
                        self.call_obj["input"] = {
                            "args": self.call.args,
                            "kwargs": self.call.kwargs,
                        }
                        self.call_obj["output"] = result

                        return application_state

                return self.run(DecoratorBasedValidatedOperation())

            return wrapped_func

        return decorator


class stack:
    def __init__(self, calls):
        self.fct = stack_functions(calls)
        self.calls = calls

    def __repr__(self):
        return f"StackedFunction({self.calls})"

    def __call__(self, *args, **kwargs):
        return self.fct(*args, **kwargs)


def stack_functions(remaining_calls=[]):
    import inspect
    from functools import partial

    if len(remaining_calls) == 0:
        raise ValueError("last stacked call must not have 'call_next' argument")
    call = remaining_calls[0]
    # check if call has 'call_next' argument
    if "call_next" not in inspect.signature(call).parameters:
        return call
    return partial(call, call_next=stack_functions(remaining_calls[1:]))


class WrappingHandler(ABC):
    def __init__(self, error: Exception):
        self.error = error

    @abstractmethod
    def __call__(self, call: OperationCall, call_next: callable):
        raise NotImplementedError


def wrappers(analysis_result: AnalysisResult):
    """Returns all handlers of the analysis result that are wrapping handlers (intercept tool execution).

    Args:
        analysis_result: The result of an analysis.

    Returns:
        Returns a list of wrapping handler functions, for which the `error` keyword argument is already bound to the relevant error.
    """
    return [
        partial(handler_call.handler, error=handler_call.error)
        for handler_call in analysis_result.handled_errors
        if is_wrapping(handler_call.handler)
    ]
