""" Utilities for working with contexts. """

import contextvars
from functools import wraps


def traced(func):
    """Decorator to run a function in an isolated context."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        context = contextvars.copy_context()
        return context.run(func, *args, **kwargs)

    return wrapper
