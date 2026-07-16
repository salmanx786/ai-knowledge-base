"""Authentication HTTP endpoints.

This layer only:
- validates input (via the Pydantic request schemas)
- delegates to AuthenticationService
- translates domain errors into HTTPException

It performs no hashing, no business logic, and never touches repositories or
the session directly -- all of that lives behind the service dependency.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_auth_service
from app.repositories.errors import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.services.auth_service import AuthenticationService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user and bootstrap their organization",
)
async def register(
    payload: RegisterRequest,
    service: AuthenticationService = Depends(get_auth_service),
) -> UserResponse:
    """Create the user, their initial organization, and OWNER membership."""
    try:
        user = await service.register_user(payload)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user with email and password",
)
async def login(
    payload: LoginRequest,
    service: AuthenticationService = Depends(get_auth_service),
) -> UserResponse:
    """Verify credentials and return the user. No token is issued yet."""
    try:
        user = await service.authenticate_user(payload)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    return UserResponse.model_validate(user)
