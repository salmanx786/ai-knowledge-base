"""Dependency providers for the authentication API layer.

Keeps service construction out of the route handlers: the endpoint declares
``Depends(get_auth_service)`` and receives a ready-to-use service bound to the
request-scoped session. The router never touches sessions or repositories.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import TokenError
from app.dependencies.db import get_db
from app.models.user import User
from app.repositories.errors import InvalidCredentialsError
from app.services.auth_service import AuthenticationService

# `auto_error=True` makes Starlette reject a missing or non-``Bearer``
# Authorization header with 401 before our code runs, so "missing header" and
# "malformed Bearer token" are handled in one place. The instance also feeds
# the OpenAPI security scheme, so Swagger UI shows an Authorize button.
_bearer_scheme = HTTPBearer(auto_error=True)


async def get_auth_service(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AuthenticationService, None]:
    """Provide an AuthenticationService bound to the request's DB session."""
    yield AuthenticationService(session)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(_bearer_scheme)
    ],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> User:
    """Resolve the authenticated user for a protected route.

    Header -> Bearer token -> verify JWT -> ``sub`` -> load user -> ``User``.

    The ``HTTPBearer`` scheme already guarantees an ``Authorization: Bearer
    <token>`` header exists and is well-formed (missing/malformed -> 401 before
    this body runs). Everything downstream -- invalid signature, expired token,
    missing/incoherent ``sub``, or a user that no longer exists -- surfaces as a
    single 401 here, so callers cannot distinguish *why* a token was rejected.
    """
    try:
        return await service.resolve_user_from_token(credentials.credentials)
    except (TokenError, InvalidCredentialsError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
