from invariant.analyzer.runtime.evaluation_context import EvaluationContext
from invariant.analyzer.runtime.input import Input
from invariant.analyzer.runtime.quantifier import Quantifier


class forall(Quantifier):
    """
    Traditional universal `forall` quantifier.

    Example:

    ```
    forall:
        (call: ToolCall):
        call is tool:send_mail
    ```

    This expression only evaluates to True if all `ToolCall` events in the trace are `tool:send_mail` events.

    """

    async def eval(
        self, input_data: Input, body, globals: dict, evaluation_context: EvaluationContext
    ):
        from invariant.analyzer.runtime.evaluation import Interpreter

        async for m in Interpreter.assignments(
            body, input_data, globals, evaluation_context=evaluation_context
        ):
            if not m.result:
                return False
        return True


# class looping(Quantifier):
#     def __init__(self, n: int):
#         self.n = n

#     def eval(self, input_data: Input, body, globals: dict, evaluation_context: EvaluationContext):
#         print("check", self, "with", globals)


class count(Quantifier):
    """
    Checks that the number of valid assignments for the body is within the specified range.

    Args:
        min (int): The minimum number of matches (inclusive).
        max (int): The maximum number of matches (inclusive).

    Example:

    ```
    count(min=2, max=4):
        (tc: ToolCall)
        tc is tool:get_inbox
    ```

    This expression only evaluates to True if there are between 2 and 4 `ToolCall` events in the trace that are `tool:get_inbox` events.
    """

    def __init__(self, min: int | None = None, max: int | None = None):
        self.min: int | None = min
        self.max: int | None = max

    async def eval(
        self, input_data: Input, body, globals: dict, evaluation_context: EvaluationContext
    ):
        from invariant.analyzer.runtime.evaluation import Interpreter

        n_matches = 0
        bad_models = 0
        interpreter: Interpreter = Interpreter.current()

        async for m in Interpreter.assignments(
            body, input_data, globals, evaluation_context=evaluation_context
        ):
            if m.result:
                n_matches += 1
                interpreter.ranges.extend(m.ranges)
            else:
                bad_models += 1
            # if we have an upper bound and we have already reached it, we can return False
            if self.max is not None and n_matches > self.max:
                return False
            # if only lower bound and we have already reached it, we can return True
            if self.min is not None and self.max is None and n_matches >= self.min:
                return True

        if self.min is not None and n_matches < self.min:
            return False

        return True
