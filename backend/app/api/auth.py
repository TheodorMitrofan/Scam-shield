"""Minimalist DB-backed login/register endpoints (direct username + password match, no keys/JWT)."""

from fastapi import APIRouter, HTTPException

from app.db import repository as repo
from app.schemas import AccountPreview, LoginRequest, RegisterRequest, UserInfo

from .deps import DbSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserInfo)
def login(body: LoginRequest, s: DbSession) -> UserInfo:
    user = repo.authenticate_user(s, body.username.strip(), body.password)
    if user is None:
        raise HTTPException(401, "Utilizator sau parolă greșită.")
    return user


@router.post("/register", response_model=UserInfo)
def register(body: RegisterRequest, s: DbSession) -> UserInfo:
    user = repo.create_user(s, body.username.strip(), body.password, body.display_name)
    if user is None:
        raise HTTPException(409, "Există deja un utilizator cu acest nume.")
    return user


@router.get("/accounts", response_model=list[AccountPreview])
def accounts(s: DbSession) -> list[AccountPreview]:
    """Lists available usernames + roles for the demo login picker (no passwords)."""
    return repo.list_accounts(s)
