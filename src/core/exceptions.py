"""Exception handler."""


class NotFoundError(Exception):
    """Represents a resource that was not found."""

    pass


class ConflictError(Exception):
    """Represents a resource that conflicts with an existing resource."""

    pass
