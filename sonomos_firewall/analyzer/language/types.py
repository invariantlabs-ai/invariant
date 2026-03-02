"""
Invariant Policy Language types.
"""


class UnknownType:
    def __str__(self):
        return "<unknown type>"

    def __repr__(self):
        return str(self)


class NamedUnknownType(UnknownType):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"<type {self.name}>"

    def __repr__(self):
        return str(self)


class FunctionType:
    def __init__(self, return_type, parameters):
        self.return_type = return_type
        self.parameters = parameters

    def __str__(self):
        return f"FunctionType({self.return_type}, {self.parameters})"

    def __repr__(self):
        return str(self)


class NoneType:
    def __str__(self):
        return "None"

    def __repr__(self):
        return str(self)


# as primitives we use
# int, float, str, bool, None
