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


class TextExtractionError(Exception):
    """Raised when a saved PDF cannot be opened or read for text extraction.

    Signals a malformed, truncated, or otherwise unreadable PDF. The API maps
    this to a 500: the file was accepted and stored, but the server could not
    process it. The uploaded file is left in place, not deleted.
    """


class NoRelevantDocumentsError(Exception):
    """Raised when a chat question retrieves no chunks to ground an answer.

    Covers both an empty index and a user who owns no documents. The API maps
    this to a 404 so the caller gets a clear "nothing to answer from" signal
    rather than an ungrounded (hallucinated) answer.
    """


class LLMConfigurationError(Exception):
    """Raised when the LLM backend is misconfigured (e.g. a missing API key).

    Signals an operator/deployment fault, not a client fault. The message is for
    logs and developers -- it may name the missing setting -- while the API maps
    this to a generic 500 that never echoes the internal detail back to callers.
    """
