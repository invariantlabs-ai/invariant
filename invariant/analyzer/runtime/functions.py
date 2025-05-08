"""
Utilities for annotating (external) standard library functions
with special runtime attributes, relevant in the context of the
invariant agent analyzer.
"""
from typing import Callable, TypeVar, ParamSpec, Awaitable, Generic

P = ParamSpec("P")
R = TypeVar("R")

def cached(func: Callable[P, Awaitable[R]] | Callable[P, R]) -> Callable[P, Awaitable[R]]:
    """
    Decorator to mark a guardrailing function or built-in predicate as interpreter-cached.

    More specifically, a function that is interpreter-cached, is a function whose result will be cached and
    reused across multiple calls to the same function with the same arguments.

    This is useful for internal guardrailing utility functions, that should have the same behavior, as @cached
    function in the context of guardrailing policies.

    One common use-case is to use a pattern like below, to use a @cached function for e.g. heavy classifier
    work, and then use the result of that function in a guardrailing function, that does some lightweight work on
    top, that cannot be cached (e.g. assigning ranges based on classifier output, thresholding, etc.).

    Example:

    ```
    @cached
    def _worker_fct():
        # do some heavy work

    def guardrailing_function(...):
        # do some work
        await _worker_fct()

        # do some lightweight work that should not be cached
        return <result of lightweight work + cached result>
    ```

    """

    return CachedFunctionWrapper(func)

class CachedFunctionWrapper(Generic[P, R]):
    """
    Wraps a function such that is is always called via the current Interpreter instance.

    This enables caching and other runtime features like function re-linking in a server context.
    """

    def __init__(self, func: Callable[P, Awaitable[R]] | Callable[P, R]):
        self.func = func
        self.func.__invariant_cache__ = True # type: ignore

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        from invariant.analyzer.runtime.evaluation import Interpreter

        return Interpreter.current().acall_function(self.func, *args, **kwargs)
