"""Pydantic schemas for authentication requests and responses."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    """Payload for student registration."""

    name: str = Field(..., min_length=1, max_length=100, description="Student's display name")
    email: str = Field(..., min_length=3, max_length=255, description="Student's email address")
    password: str = Field(..., min_length=6, max_length=128, description="Account password")

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Invalid email format")
        return cleaned


class RegisterResponse(BaseModel):
    """Response returned upon successful registration."""

    id: str
    name: str
    email: str
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"


class LoginRequest(BaseModel):
    """Payload for student login."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class LoginResponse(BaseModel):
    """Response returned upon successful login containing student info and JWT token."""

    id: str
    name: str
    email: str
    access_token: str
    token_type: str = "bearer"
