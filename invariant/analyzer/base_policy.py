from invariant.analyzer.stdlib.invariant.errors import AnalysisResult, ErrorInformation


class BasePolicy:
    """
    Common base class for Policy implementations.

    See 'LocalPolicy' and 'RemotePolicy' for concrete implementations.
    """

    def analyze(self, input: dict, raise_unhandled=False, **policy_parameters):
        raise NotImplementedError

    def analyze_pending(
        self,
        past_events: list[dict],
        pending_events: list[dict],
        raise_unhandled=False,
        **policy_parameters,
    ):
        raise NotImplementedError

    async def a_analyze(self, input: list[dict], raise_unhandled=False, **policy_parameters):
        raise NotImplementedError

    async def a_analyze_pending(
        self,
        past_events: list[dict],
        pending_events: list[dict],
        raise_unhandled=False,
        **policy_parameters,
    ):
        raise NotImplementedError

    def incremental(self) -> "IncrementalPolicy":
        """
        An incremental policy wrapper (only returns new errors compared to the previous invocation).
        """
        return IncrementalPolicy(self)


class IncrementalPolicy(BasePolicy):
    """
    Allows to invoke Policy.analyze multiple times with the same policy.

    Only new errors compared to the previous invocation are returned.
    """

    def __init__(self, policy):
        self.policy = policy
        self.policy.cached = True
        self.previous_errors = set()

    def __str__(self):
        return f"IncrementalPolicy({self.policy}, previous_errors={self.previous_errors})"

    def analyze(self, input: dict, raise_unhandled=False, **policy_parameters):
        """
        Analyzes the input and returns a list of new errors.
        """
        result = self.policy.analyze(input, raise_unhandled=raise_unhandled, **policy_parameters)
        result = self._filter_result(result)
        return result

    async def a_analyze(self, input: list[dict], raise_unhandled=False, **policy_parameters):
        """
        Asynchronously analyzes the input and returns a list of new errors.
        """
        result = await self.policy.a_analyze(
            input, raise_unhandled=raise_unhandled, **policy_parameters
        )
        result = self._filter_result(result)
        return result

    def analyze_pending(
        self,
        past_events: list[dict],
        pending_events: list[dict],
        raise_unhandled=False,
        **policy_parameters,
    ):
        """
        Analyzes the pending events and returns a list of new errors.
        """
        result = self.policy.analyze_pending(
            past_events, pending_events, raise_unhandled=raise_unhandled, **policy_parameters
        )
        result = self._filter_result(result)
        return result

    async def a_analyze_pending(
        self,
        past_events: list[dict],
        pending_events: list[dict],
        raise_unhandled=False,
        **policy_parameters,
    ):
        """
        Asynchronously analyzes the pending events and returns a list of new errors.
        """
        result = await self.policy.a_analyze_pending(
            past_events, pending_events, raise_unhandled=raise_unhandled, **policy_parameters
        )
        result = self._filter_result(result)
        return result

    def error_key(self, error: ErrorInformation):
        """
        Generates a unique key for the error.
        """
        # use error.key if available, otherwise use the object identity
        # NOTE: this means if the returned error does not have a key it may show up multiple times
        # when calling analyze() multiple times. To fix that, make sure to provide 'key' on every
        # error to allow recognizing it across multiple invocations.
        return error.key if error.key is not None else id(error)

    def _filter_result(self, result: AnalysisResult) -> AnalysisResult:
        """
        Filters the result to only include new errors, compared to the previous invocation.
        """
        new_errors = [
            error for error in result.errors if self.error_key(error) not in self.previous_errors
        ]
        result.errors = list(new_errors)
        self.previous_errors.update([self.error_key(error) for error in new_errors])
        return result
