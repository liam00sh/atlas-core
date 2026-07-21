class ToolError(Exception):
    """Error base del framework de herramientas."""


class ToolRegistrationError(ToolError):
    pass


class ToolNotFoundError(ToolError):
    pass


class ToolDisabledError(ToolError):
    pass


class ToolPermissionError(ToolError):
    pass


class ToolValidationError(ToolError):
    pass


class ToolExecutionError(ToolError):
    pass
