import importlib

from invariant.analyzer.language.scope import ExternalReference
from invariant.analyzer.language.ast import Node

class SymbolTable:
    """
    Links external identifiers and functions to their implementations
    """

    def link(self, function, node: None | Node):
        """Links to the given function by default."""
        return function

    def link_import(self, ref: ExternalReference):
        """Links to the given module by default."""
        module_name = ref.module
        # try to import from the default sys path
        module = resolve_default_path(ref)
        if module is not None:
            return module

        raise ImportError(f"Module '{module_name}' could not be resolved") from None

    def allows_module_interfacing(self):
        """
        Return true iff the symbol table allows policies to import and interact with
        raw Python modules (without any restrictions).

        DANGEROUS: this will allow `import os; os.system(...)` and similar calls.
        """
        return True


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
