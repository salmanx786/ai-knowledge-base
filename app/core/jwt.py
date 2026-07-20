"""JSON Web Token primitives for access tokens.

Like ``security.py``, this module intentionally contains *only* the low-level
token primitives -- creating, decoding, and verifying signed JWTs. It knows
nothing about users, requests, or HTTP; callers (the auth service) map domain
concepts like "user id" onto the ``sub`` claim.

We use ``PyJWT`` rather than ``python-jose``: PyJWT is narrowly scoped to JWT,
actively maintained, and has a cleaner security track record.

Algorithm and lifetime come from ``settings`` so they are configured in exactly
one place. HS256 (symmetric HMAC) is appropriate while a single service both
signs and verifies; the same ``jwt_secret`` is used for both directions.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.config.settings import settings


class TokenError(Exception):
    """Raised when a token cannot be decoded, verified, or has expired.

    A single exception type keeps callers from having to know PyJWT's internal
    exception hierarchy, and mirrors the "one domain error" style used by the
    repositories layer.
    """


def create_access_token(subject: str | int) -> tuple[str, int]:
    """Create a signed access token for ``subject`` (typically a user id).

    Returns a ``(token, expires_in_seconds)`` tuple so the caller can report the
    lifetime to the client without re-deriving it. The token carries three
    registered claims:

    - ``sub``  -- the subject the token is about (stringified user id)
    - ``iat``  -- issued-at time, so age can be reasoned about
    - ``exp``  -- expiry time, enforced automatically by ``verify_access_token``

    Times are timezone-aware UTC. PyJWT encodes ``iat``/``exp`` as NumericDate
    (Unix seconds) per the JWT spec.
    """
    expires_in = settings.jwt_access_token_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        # `sub` must be a string per the JWT spec; ints are a common footgun.
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a token, returning its claims.

    Verifies the signature *and* the ``exp`` claim (PyJWT checks expiry by
    default). Any failure -- bad signature, malformed token, or expiry -- is
    normalized into :class:`TokenError`. ``algorithms`` is pinned to the
    configured algorithm so an attacker cannot force a weaker/``none`` alg.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except InvalidTokenError as exc:
        # InvalidTokenError is PyJWT's base class for signature/format errors.
        raise TokenError("Token is invalid.") from exc


def verify_access_token(token: str) -> str:
    """Verify an access token and return its subject (``sub``) claim.

    This is the convenience entry point for the common case: "give me the token,
    tell me who it belongs to, and raise if it is not trustworthy." Raises
    :class:`TokenError` if the token is invalid/expired or is missing ``sub``.
    """
    claims = decode_token(token)
    subject = claims.get("sub")
    if subject is None:
        raise TokenError("Token is missing the subject claim.")
    return subject
