"""
Utilities for annotating (external) standard library functions
with special runtime attributes, relevant in the context of the
invariant agent analyzer.
"""


def cache(func):
    """
    Decorator to mark a function as non-cacheable.

    This is useful for functions that have side-effects.

    When marked as @nocache, a function may be invoked many times
    during the evaluation of a policy rule, even for partial variable
    assignemnts that are not part of the final result.
    """
    func.__invariant_cache__ = True
    return func
