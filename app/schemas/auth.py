"""Pydantic v2 request/response schemas for the authentication foundation.

These are transport/DTO objects only. They never expose ``hashed_password``
and carry no ORM coupling beyond ``from_attributes`` on the response.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload to register a new user and bootstrap their first organization."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    # Registration also creates the user's initial tenant, so the org name is
    # part of the signup payload.
    organization_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Credentials for authenticating an existing user."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Public representation of a user. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
