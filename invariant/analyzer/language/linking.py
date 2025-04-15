"""
Invariant Policy Language linker for Python-based execution.
"""

import importlib
import os
from importlib import util
from typing import Optional

from invariant.analyzer.language.scope import ExternalReference
from invariant.analyzer.runtime.symbol_table import SymbolTable

STDLIB_PATH = os.path.join(os.path.dirname(__file__), "../stdlib")


def resolve(ref: ExternalReference, symbol_table: Optional[SymbolTable] = None):
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
        return symbol_table.link_import(ref)


def link(scope, symbol_table: SymbolTable):
    assert symbol_table is not None, "Symbol table must be provided for linking."

    global_scope = {}
    for name, decl in scope.all():
        if isinstance(decl.value, ExternalReference):
            global_scope[decl] = resolve(decl.value, symbol_table)
        else:
            global_scope[decl] = decl.value

    return global_scope
