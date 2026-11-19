"""Read/delete what the user saved with consent: applications → contacts → conversations → messages."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db import repository as repo
from app.schemas import (
    ApplicationSummary,
    Channel,
    ContactSummary,
    ConversationDetail,
    ConversationSummary,
    DeleteResponse,
)

from .deps import ClientId, DbSession

router = APIRouter(tags=["history"])


@router.get("/apps", response_model=list[ApplicationSummary])
def list_apps(client_id: ClientId, s: DbSession):
    return repo.list_applications(s, client_id)


@router.get("/apps/{code}/contacts", response_model=list[ContactSummary])
def list_contacts(code: Channel, client_id: ClientId, s: DbSession):
    return repo.list_contacts(s, client_id, code.value)


@router.get("/contacts/{contact_id}/conversations", response_model=list[ConversationSummary])
def list_conversations(contact_id: UUID, client_id: ClientId, s: DbSession):
    out = repo.list_conversations(s, client_id, contact_id)
    if out is None:
        raise HTTPException(404, "Contact inexistent.")
    return out


@router.get("/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: UUID, client_id: ClientId, s: DbSession):
    out = repo.load_conversation(s, client_id, conv_id)
    if out is None:
        raise HTTPException(404, "Conversație inexistentă.")
    return out


@router.delete("/conversations/{conv_id}", response_model=DeleteResponse)
def delete_conversation(conv_id: UUID, client_id: ClientId, s: DbSession):
    return DeleteResponse(deleted=repo.delete_conversation(s, client_id, conv_id))


@router.delete("/contacts/{contact_id}", response_model=DeleteResponse)
def delete_contact(contact_id: UUID, client_id: ClientId, s: DbSession):
    return DeleteResponse(deleted=repo.delete_contact(s, client_id, contact_id))


@router.delete("/history", response_model=DeleteResponse)
def delete_all(client_id: ClientId, s: DbSession):
    """“Șterge tot ce am salvat” — removes every conversation and contact of this client."""
    return DeleteResponse(deleted=repo.delete_all(s, client_id))
