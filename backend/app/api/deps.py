from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import Database
from app.detector.client import DetectorClient
from app.schemas.storage import DEFAULT_RETENTION_HOURS, MAX_RETENTION_HOURS, SaveOptions


def get_detector(request: Request) -> DetectorClient:
    return request.app.state.detector


def get_db(request: Request) -> Database:
    return request.app.state.db


def save_options(
    save: Annotated[bool, Query(description="Consent checkbox: true = store this conversation")] = False,
    retention_hours: Annotated[int, Query(ge=1, le=MAX_RETENTION_HOURS)] = DEFAULT_RETENTION_HOURS,
    x_client_id: Annotated[UUID | None, Header()] = None,
) -> SaveOptions:
    return SaveOptions(save=save, client_id=x_client_id, retention_hours=retention_hours)


def required_client_id(x_client_id: Annotated[UUID | None, Header()] = None) -> UUID:
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
ClientId = Annotated[UUID, Depends(required_client_id)]
DbSession = Annotated[Session, Depends(db_session)]
