"""Exception handler."""


class AppBaseError(Exception):
    """Base class for all exceptions in the application."""

    status_code: int = 500


class NotFoundError(AppBaseError):
    """Not found error. Represents a resource that was not found."""

    status_code = 404


class ConflictError(AppBaseError):
    """Conflict error. Represents a resource that conflicts with an existing resource."""

    status_code = 409


class ForbiddenError(AppBaseError):
    """Forbidden error. Represents an action that is not allowed."""

    status_code = 403


class UnauthorizedError(AppBaseError):
    """Unauthorized error. Represents an action that is not authenticated."""

    status_code = 401


class TooManyRequestsError(AppBaseError):
    """Too many requests error."""

    status_code = 429
