"""Security utilities."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plain text password."""
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password."""
    try:
        _password_hasher.verify(hashed_password, password)
        return True
    except VerifyMismatchError:
        return False
