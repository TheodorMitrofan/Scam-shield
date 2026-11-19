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

from .deps import DbSession, ScopeClientId

router = APIRouter(tags=["history"])


@router.get("/history/conversations", response_model=list[ConversationDetail])
def list_all_conversations(scope: ScopeClientId, s: DbSession):
    """Cross-tenant feed: admin gets all users' saved queries; user gets only their own."""
    return repo.list_saved_conversations(s, scope)


@router.get("/apps", response_model=list[ApplicationSummary])
def list_apps(scope: ScopeClientId, s: DbSession):
    return repo.list_applications(s, scope)


@router.get("/apps/{code}/contacts", response_model=list[ContactSummary])
def list_contacts(code: Channel, scope: ScopeClientId, s: DbSession):
    return repo.list_contacts(s, scope, code.value)


@router.get("/contacts/{contact_id}/conversations", response_model=list[ConversationSummary])
def list_conversations(contact_id: UUID, scope: ScopeClientId, s: DbSession):
    out = repo.list_conversations(s, scope, contact_id)
    if out is None:
        raise HTTPException(404, "Contact inexistent.")
    return out


@router.get("/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: UUID, scope: ScopeClientId, s: DbSession):
    out = repo.load_conversation(s, scope, conv_id)
    if out is None:
        raise HTTPException(404, "Conversație inexistentă.")
    return out


@router.delete("/conversations/{conv_id}", response_model=DeleteResponse)
def delete_conversation(conv_id: UUID, scope: ScopeClientId, s: DbSession):
    return DeleteResponse(deleted=repo.delete_conversation(s, scope, conv_id))


@router.delete("/contacts/{contact_id}", response_model=DeleteResponse)
def delete_contact(contact_id: UUID, scope: ScopeClientId, s: DbSession):
    return DeleteResponse(deleted=repo.delete_contact(s, scope, contact_id))


@router.delete("/history", response_model=DeleteResponse)
def delete_all(scope: ScopeClientId, s: DbSession):
    """“Șterge tot ce am salvat” — removes conversations visible to this client/scope."""
    return DeleteResponse(deleted=repo.delete_all(s, scope))
