from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db import repository as repo
from app.db.session import Database
from app.detector.client import DetectorClient
from app.schemas import UserInfo
from app.schemas.storage import DEFAULT_RETENTION_HOURS, MAX_RETENTION_HOURS, SaveOptions


def get_detector(request: Request) -> DetectorClient:
    return request.app.state.detector


def get_db(request: Request) -> Database:
    return request.app.state.db


def optional_user(
    db: Annotated[Database, Depends(get_db)],
    x_user_id: Annotated[UUID | None, Header()] = None,
) -> UserInfo | None:
    if x_user_id is None:
        return None
    if not db.ready and not db.ping():
        raise HTTPException(503, "Baza de date nu este disponibilă.")
    with db.sessionmaker() as s:
        user = repo.get_user(s, x_user_id)
    if user is None:
        raise HTTPException(401, "Utilizator invalid sau sesiune expirată.")
    return user


def save_options(
    user: Annotated[UserInfo | None, Depends(optional_user)],
    save: Annotated[bool, Query(description="Consent checkbox: true = store this conversation")] = False,
    retention_hours: Annotated[int, Query(ge=1, le=MAX_RETENTION_HOURS)] = DEFAULT_RETENTION_HOURS,
    x_client_id: Annotated[UUID | None, Header()] = None,
) -> SaveOptions:
    cid = user.id if user is not None else x_client_id
    return SaveOptions(save=save, client_id=cid, retention_hours=retention_hours)


def history_scope(
    user: Annotated[UserInfo | None, Depends(optional_user)],
    x_client_id: Annotated[UUID | None, Header()] = None,
) -> UUID | None:
    """Returns None for admin (sees all tenants), user.id for user, or x_client_id for legacy clients."""
    if user is not None:
        return None if user.role == "admin" else user.id
    if x_client_id is None:
        raise HTTPException(400, "Lipsește header-ul X-Client-Id.")
    return x_client_id


def db_session(db: Annotated[Database, Depends(get_db)]) -> Iterator[Session]:
    """Session for history endpoints; commits on success (listing also purges expired rows)."""
    if not db.ready and not db.ping():
        raise HTTPException(503, "Baza de date nu este disponibilă.")
    with db.sessionmaker.begin() as s:
        yield s


Detector = Annotated[DetectorClient, Depends(get_detector)]
Db = Annotated[Database, Depends(get_db)]
Save = Annotated[SaveOptions, Depends(save_options)]
CurrentUser = Annotated[UserInfo | None, Depends(optional_user)]
ScopeClientId = Annotated[UUID | None, Depends(history_scope)]
DbSession = Annotated[Session, Depends(db_session)]
