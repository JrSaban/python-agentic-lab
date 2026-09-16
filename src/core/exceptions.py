"""Exception handler."""


class NotFoundError(Exception):
    """Représente une ressource qui n'a pas été trouvée."""

    pass


class ConflictError(Exception):
    """Représente une ressource qui entre en conflit avec une ressource existante."""

    pass


class ForbiddenError(Exception):
    """Représente une action non autorisée."""

    pass
