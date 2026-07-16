"""Dependency providers for the authentication API layer.

Keeps service construction out of the route handlers: the endpoint declares
``Depends(get_auth_service)`` and receives a ready-to-use service bound to the
request-scoped session. The router never touches sessions or repositories.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.services.auth_service import AuthenticationService


async def get_auth_service(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AuthenticationService, None]:
    """Provide an AuthenticationService bound to the request's DB session."""
    yield AuthenticationService(session)
