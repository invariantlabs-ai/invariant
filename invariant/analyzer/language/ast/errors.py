"""
Error types and error handling for the IPL parser.
"""

import io

from invariant.analyzer.language.ast.base import Node


class PolicyError(ValueError):
    """
    If PolicyError is raised as part of a AST visitor, the resulting error message will be
    formatted as an issue with a policy file at the currently examined AST node (if available).
    """

    def __init__(self, message, node=None):
        super().__init__(message)
        # the associated AST node
        self.node: Node | None = node

    def as_dict(self):
        return {
            "message": str(self),
            "type": type(self).__name__,
            "line": self.node.location.line,
            "column": self.node.location.column,
            "path": self.node.location.code.path,
        }

    @staticmethod
    def to_dict(e: Exception):
        if isinstance(e, PolicyError):
            return e.as_dict()
        return {"message": str(e), "type": type(e).__name__}

    @staticmethod
    def error_report(errors: list[Exception]):
        output = io.StringIO()

        for error in errors:
            # handle 'PolicyError'
            if hasattr(error, "node") and error.node is not None:
                node: Node = error.node
                node.location.print_error(error, margin=1, output=output)
                output.write("\n")
            # handle other, e.g. lark parsing errors
            else:
                # Location.UNKNOWN.print_error(error, margin=1, output=output)
                output.write(str(error) + "\n")

        return output.getvalue()