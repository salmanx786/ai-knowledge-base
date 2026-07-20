"""Domain errors raised by the service/repository layer.

Kept transport-agnostic on purpose: no HTTP status codes here. The API layer
maps these to responses. This keeps services/repositories usable outside of
FastAPI (scripts, workers, tests).
"""


class AuthError(Exception):
    """Base class for authentication/registration domain errors."""


class EmailAlreadyExistsError(AuthError):
    """Raised when registering an email that already exists."""


class InvalidCredentialsError(AuthError):
    """Raised when login fails due to unknown email or wrong password."""


class DocumentNotFoundError(Exception):
    """Raised when a document does not exist or is not owned by the caller.

    Deliberately does not distinguish the two cases: the service raises the
    same error whether the row is absent or belongs to another user, so the API
    can return an identical 404 and never leak the existence of other users'
    documents.
    """
