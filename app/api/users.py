"""User-facing HTTP endpoints.

Currently just the "who am I" route. Like the auth router, this layer only
wires a dependency to a response schema: authentication happens entirely inside
``get_current_user`` (header -> JWT -> user), so the handler receives an
already-authenticated ``User`` and never touches tokens, sessions, or
repositories directly.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the currently authenticated user",
)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Return the profile of the user identified by the bearer token."""
    return UserResponse.model_validate(current_user)
