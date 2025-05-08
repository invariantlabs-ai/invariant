"""
Invariant Policy Language scoping.
"""

import inspect

from invariant.analyzer.language.types import FunctionType, UnknownType

IPL_BUILTINS = [
    "LLM",
    "Message",
    "ToolCall",
    "Function",
    "ToolOutput",
    "Input",
    "Violation",
    "PolicyViolation",
    "UpdateMessage",
    "UpdateMessageHandler",
    "TextChunk",
    "Image",
    "any",
    "empty",
    "match",
    "json_loads",
    "len",
    "find",
    "min",
    "max",
    "sum",
    "print",
    "tuple",
    "tool_call",
    "text",
    "image",
    "Tool",
    "ToolParameter",
]


class ExternalReference:
    def __init__(self, module, obj=None):
        self.module = module
        self.obj = obj

    def __str__(self) -> str:
        if self.obj is not None:
            return self.module + "." + self.obj
        return self.module

    def __repr__(self) -> str:
        return str(self)


class VariableDeclaration:
    def __init__(self, name, type_ref=None, value=None):
        self.name = name
        self.type_ref = type_ref or UnknownType()
        self.value = value or None

    def __lt__(self, other):
        assert isinstance(other, VariableDeclaration), f"Cannot compare {self} with {other}"
        return self.name < other.name

    def __str__(self):
        value_repr = (
            str(self.value).encode("unicode_escape").decode("utf-8")
            if self.value is not None
            else "<uninitialized>"
        )
        type_repr = str(self.type_ref)
        return f"VariableDeclaration({id(self)} {self.name}: {type_repr})"

    def __repr__(self):
        return str(self)

    @classmethod
    def from_signature(cls, signature: "FunctionSignature | Identifier", value=None):
        from invariant.analyzer.language.ast import FunctionSignature, Identifier

        if isinstance(signature, FunctionSignature):  # predicate declaration
            return cls(signature.name.name, value=value)
        elif isinstance(signature, Identifier):  # constant declaration
            return cls(signature.name, value=value)
        else:
            raise ValueError(f"Invalid signature: {signature}")


class Scope:
    def __init__(self, parent=None, name=None):
        self.parent = parent
        self.declarations = {}
        self.name = name

    def register(self, decl):
        assert type(decl) is VariableDeclaration
        self.declarations[decl] = decl

    def resolve(self, name) -> VariableDeclaration:
        if name in self.declarations:
            return self.declarations[name]
        if self.parent:
            return self.parent.resolve(name)

        return self.resolve_builtin(name)

    def resolve_type(self, name):
        declaration = self.resolve(name)
        if declaration is None:
            return self.resolve_builtin(name)
        return declaration.type_ref

    def resolve_builtin(self, name):
        if name == "str":
            return VariableDeclaration(name, type, str)
        elif name == "int":
            return VariableDeclaration(name, type, int)
        elif name == "float":
            return VariableDeclaration(name, type, float)
        elif name == "bool":
            return VariableDeclaration(name, type, bool)
        elif name == "list":
            return VariableDeclaration(name, type, list)
        elif name == "dict":
            return VariableDeclaration(name, type, dict)
        return None

    def __str__(self):
        name = ""
        if self.name is not None:
            name = self.name + " "

        if self.parent:
            return (
                f"Scope({name}declarations: {self.declarations}, parent: {self.parent.__str__()})"
            )
        return f"Scope({name}declarations: {self.declarations})"

    def __repr__(self):
        return str(self)

    def all(self):
        for name, decl in self.declarations.items():
            yield name, decl

        if self.parent is None:
            return

        for name, decl in self.parent.all():
            yield name, decl


class BuiltInScope(Scope):
    def __init__(self):
        super().__init__()
        for name in IPL_BUILTINS:
            self.declarations[name] = VariableDeclaration(
                name, UnknownType(), ExternalReference("invariant.builtins", name)
            )

    def register(self, name):
        def decorator(fn):
            self.declarations[name] = VariableDeclaration(name, self.create_type(fn), fn)
            return fn

        return decorator

    def create_type(self, python_obj):
        if type(python_obj) == type:
            return python_obj
        elif callable(python_obj):
            signature = inspect.signature(python_obj)
            return_type = (
                signature.return_annotation
                if signature.return_annotation != inspect._empty
                else UnknownType()
            )
            return FunctionType(return_type, [UnknownType() for _ in signature.parameters])


GlobalScope = BuiltInScope()

"""
Exposes the identifier `input` to policy rules, allowing them
to access policy parameters such as on the authentication status.

The actual value of `input` is inserted by the `Interpreter` during
rule evaluation and not known ahead of time.
"""
InputData = object()
GlobalScope.register("input")(InputData)


@GlobalScope.register("AccessDenied")
class AccessDenied(Exception):
    pass
