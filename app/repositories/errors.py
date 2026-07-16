"""Domain errors raised by the auth foundation.

Kept transport-agnostic on purpose: no HTTP status codes here. The API layer
(added later) maps these to responses. This keeps services/repositories
usable outside of FastAPI (scripts, workers, tests).
"""


class AuthError(Exception):
    """Base class for authentication/registration domain errors."""


class EmailAlreadyExistsError(AuthError):
    """Raised when registering an email that already exists."""


class InvalidCredentialsError(AuthError):
    """Raised when login fails due to unknown email or wrong password."""
