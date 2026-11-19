"""Minimalist DB-backed user + role DTOs (admin | user, direct username/password match)."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

UserRole = Literal["admin", "user"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=2, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)


class UserInfo(BaseModel):
    id: UUID
    username: str
    role: UserRole
    display_name: str


class AccountPreview(BaseModel):
    username: str
    role: UserRole
    display_name: str
