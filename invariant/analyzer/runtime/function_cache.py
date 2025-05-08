import inspect
from typing import Awaitable, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class FunctionCache:
    """
    The function cache is responsible for handling function calls in policy rules
    and to retrieve previously cached results if available.

    It is used to cache the results of function calls to avoid redundant computations
    within a single policy execution and across multiple policy executions over time.
    """

    def __init__(self, cache=None):
        self.cache = cache or {}

    def clear(self):
        self.cache = {}

    def arg_key(self, arg):
        # cache primitives by value
        if type(arg) is int or type(arg) is float or type(arg) is str:
            return arg
        # cache lists by id
        elif type(arg) is list:
            return tuple(self.arg_key(a) for a in arg)
        # cache dictionaries by id
        elif type(arg) is dict:
            return tuple((k, self.arg_key(v)) for k, v in sorted(arg.items(), key=lambda x: x[0]))
        # cache all other objects by id
        return id(arg)

    def call_key(self, function, args, kwargs):
        id_args = (self.arg_key(arg) for arg in args)
        id_kwargs = ((self.arg_key(k), self.arg_key(v)) for k, v in kwargs.items())
        return (id(function), *id_args, *id_kwargs)

    async def call(self, function, args, **kwargs):
        raise NotImplementedError("call() not implemented")

    async def get(self, key):
        return self.cache.get(key)

    async def set(self, key, value):
        self.cache[key] = value

    async def acall(
        self,
        function: Callable[P, Awaitable[R]] | Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        # if function is not marked with @cached we just call it directly (see ./functions.py module)
        if not hasattr(function, "__invariant_cache__"):
            return await call_either_way(function, *args, **kwargs)

        key = self.call_key(function, args, kwargs)
        value = await self.get(key)

        if value is not None:
            return value
        else:
            value = await call_either_way(function, *args, **kwargs)
            await self.set(key, value)
            return value


async def call_either_way(
    func: Callable[P, Awaitable[R]] | Callable[P, R], *args: P.args, **kwargs: P.kwargs
) -> R:
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)  # type: ignore
