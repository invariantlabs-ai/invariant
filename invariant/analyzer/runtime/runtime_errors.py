class ExcessivePolicyError(ValueError):
    """
    This exception is raised when a policy attempts unsafe or excessive operations (e.g. use unavailable properties or methods on objects).
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return "Excessive Policy: " + self.message


ExcessivePolicyError.catchphrase = "Excessive Policy: "


class MissingPolicyParameter(KeyError):
    """
    This exception is raised when a policy is missing a required parameter.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return "Missing Policy Parameter: " + self.message


MissingPolicyParameter.catchphrase = "Missing Policy Parameter: "


class InvariantAttributeError(AttributeError):
    """
    This exception is raised when an attribute is not found or accessible on an object (it may exist in Python, but still be unavailable in the policy context).
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return "Invariant Attribute Error: " + self.message


InvariantAttributeError.catchphrase = "Invariant Attribute Error: "


class PolicyExecutionError(Exception):
    """
    This exception is raised when a policy execution fails.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


PolicyExecutionError.catchphrase = "Error during analysis:"
