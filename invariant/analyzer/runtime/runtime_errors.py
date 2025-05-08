class ExcessivePolicyError(ValueError):
    """
    This exception is raised when a policy attempts unsafe or excessive operations (e.g. use unavailable properties or methods on objects).
    """

    catchphrase = "Excessive Policy: "

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

    catchphrase = "Missing Policy Parameter: "

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return "Missing Policy Parameter: " + self.message


MissingPolicyParameter.catchphrase = "Missing Policy Parameter: "


class InvariantInputValidationError(AttributeError):
    """
    This exception is raised when a input trace cannot be parsed.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return "Input Validation Error: " + self.message


InvariantInputValidationError.catchphrase = "Input Validation Error: "


class InvariantAttributeError(AttributeError):
    """
    This exception is raised when an attribute is not found or accessible on an object (it may exist in Python, but still be unavailable in the policy context).
    """

    catchphrase = "Invariant Attribute Error: "

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return "Invariant Attribute Error: " + self.message


class PolicyExecutionError(Exception):
    """
    This exception is raised when a policy execution fails.
    """

    catchphrase = "Error during analysis: "

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message
