"""
Invariant Policy Language linker for Python-based execution.
"""

import importlib
import os
from importlib import util

from invariant.analyzer.language.scope import ExternalReference

STDLIB_PATH = os.path.join(os.path.dirname(__file__), "../stdlib")


def resolve(ref: ExternalReference):
    # import the module from STDLIB_PATH/{ref.module} and return the object
    # ref.obj if it is not None
    module_name = ref.module
    filepath = os.path.join(STDLIB_PATH, module_name.replace(".", "/") + ".py")
    if not os.path.exists(filepath):
        filepath = os.path.join(STDLIB_PATH, module_name.replace(".", "/") + "/__init__.py")
    spec = util.spec_from_file_location(module_name, filepath)

    try:
        if spec is None:
            raise FileNotFoundError
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if ref.obj:
            return getattr(module, ref.obj)
        return module
    except FileNotFoundError:
        # try to import from the default sys path
        module = resolve_default_path(ref)
        if module is not None:
            return module

        raise ImportError(
            f"Module '{module_name}' could not be resolved (stdlib path: {os.path.abspath(STDLIB_PATH)})"
        ) from None


def resolve_default_path(ref: ExternalReference):
    # import the module from {ref.module} and return the object ref.obj if it is not None
    module_name = ref.module

    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if ref.obj:
            return getattr(module, ref.obj)
        return module
    except ModuleNotFoundError:
        return None
    except FileNotFoundError:
        return None


def link(scope):
    symbol_table = {}
    for name, decl in scope.all():
        if isinstance(decl.value, ExternalReference):
            symbol_table[decl] = resolve(decl.value)
        else:
            symbol_table[decl] = decl.value

    return symbol_table
