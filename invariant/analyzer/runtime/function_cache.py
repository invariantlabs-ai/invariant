import asyncio
import inspect
from typing import Awaitable, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class DictLock:
    def __init__(self):
        self.locks = {}
        self.main_lock = asyncio.Lock()

    async def key(self, key):
        async with self.main_lock:
            if key not in self.locks:
                self.locks[key] = DictLockValue(key)
            return self.locks[key]


class DictLockValue:
    def __init__(self, value):
        self.value = value
        self.lock = asyncio.Lock()

    async def __aenter__(self):
        await self.lock.acquire()

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.lock.release()
        return False


class FunctionCache:
    """
    The function cache is responsible for handling function calls in policy rules
    and to retrieve previously cached results if available.

    It is used to cache the results of function calls to avoid redundant computations
    within a single policy execution and across multiple policy executions over time.
    """

    def __init__(self, cache=None):
        self.cache = cache or {}
        self.cache_locks = DictLock()

    def clear(self):
        self.cache = {}

    def arg_key(self, arg):
        # cache primitives by value
        if type(arg) is int or type(arg) is float or type(arg) is str or type(arg) is bool:
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

        async with await self.cache_locks.key(key):
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
