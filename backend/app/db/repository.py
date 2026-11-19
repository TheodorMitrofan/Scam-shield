"""All DB reads/writes. Routes never touch ORM objects; they get/give DTOs from app.schemas.

Every function is scoped by `client_id` — a user only ever sees or deletes what they saved.
"""

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.schemas import (
    AccountPreview,
    AnalysisResult,
    ApplicationSummary,
    ContactSummary,
    ConversationDetail,
    ConversationSummary,
    Scenario,
    UserInfo,
)

from .models import (
    Application,
    AttributeDefinition,
    AttributeValue,
    Contact,
    Conversation,
    MessageRow,
    User,
    user_uuid,
)

# ---------------------------------------------------------------------------------------------
# EAV helpers
# ---------------------------------------------------------------------------------------------


def _definitions(s: Session, app_id: int, entity: str) -> dict[str, AttributeDefinition]:
    rows = s.scalars(
        select(AttributeDefinition).where(
            AttributeDefinition.entity == entity,
            or_(AttributeDefinition.application_id == app_id, AttributeDefinition.application_id.is_(None)),
        )
    )
    return {d.name: d for d in rows}


def _set_attr(s: Session, defs: dict[str, AttributeDefinition], name: str, entity_id: uuid.UUID, value: Any) -> None:
    d = defs.get(name)
    if d is None or value is None:
        return
    v = AttributeValue(attribute_id=d.id, entity_id=entity_id)
    if d.data_type == "number":
        v.value_number = float(value)
    elif d.data_type == "json":
        v.value_json = value
    else:
        v.value_text = str(value)
    s.add(v)


def _get_attrs(s: Session, entity_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, dict[str, Any]]:
    ids = list(entity_ids)
    out: dict[uuid.UUID, dict[str, Any]] = {i: {} for i in ids}
    if not ids:
        return out
    rows = s.execute(
        select(AttributeValue, AttributeDefinition)
        .join(AttributeDefinition, AttributeValue.attribute_id == AttributeDefinition.id)
        .where(AttributeValue.entity_id.in_(ids))
    )
    for v, d in rows:
        val = {"number": v.value_number, "json": v.value_json}.get(d.data_type, v.value_text)
        out[v.entity_id][d.name] = val
    return out


def _delete_attrs(s: Session, entity_ids: Iterable[uuid.UUID]) -> None:
    ids = list(entity_ids)
    if ids:
        s.execute(delete(AttributeValue).where(AttributeValue.entity_id.in_(ids)))


def _email_subject(scenario: Scenario) -> str:
    # The official format has no subject; derive it from the first sentence like the UI does.
    text = (scenario.messages[0].text if scenario.messages else "").strip()
    first = text.split(". ")[0]
    return (first[:117] + "…") if len(first) > 120 else first


# ---------------------------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------------------------


def save_conversation(
    s: Session, client_id: uuid.UUID, scenario: Scenario, result: AnalysisResult, retention_hours: int
) -> uuid.UUID:
    """Upsert application→contact→conversation→messages (+ EAV attributes). Caller commits.

    Re-analysing the same scenario id with the same contact replaces the conversation (no duplicates).
    """
    app = s.scalars(select(Application).where(Application.code == scenario.channel.value)).one()
    address = scenario.sender.address or ""
    name = scenario.sender.name or ""

    contact = s.scalars(
        select(Contact).where(
            Contact.client_id == client_id,
            Contact.application_id == app.id,
            Contact.address == address,
            func.coalesce(Contact.display_name, "") == name,
        )
    ).first()
    if contact is None:
        contact = Contact(client_id=client_id, application_id=app.id, address=address, display_name=name or None)
        s.add(contact)
    contact.known_contact = scenario.sender.known_contact
    s.flush()

    conv = s.scalars(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.client_id == client_id,
            Conversation.contact_id == contact.id,
            Conversation.external_id == scenario.id,
        )
    ).first()
    if conv is None:
        conv = Conversation(client_id=client_id, contact_id=contact.id, application_id=app.id, external_id=scenario.id)
        s.add(conv)
    else:
        _delete_attrs(s, [conv.id, *(m.id for m in conv.messages)])
        conv.messages.clear()
        s.flush()

    conv.expires_at = datetime.now(UTC) + timedelta(hours=retention_hours)
    conv.verdict = result.verdict.value
    conv.scam_type = result.scam_type.value
    conv.risk_score = result.risk_score
    conv.first_alert = result.first_alert
    conv.red_flags = [f.value for f in result.red_flags]
    conv.warning_ro = result.warning.ro
    conv.warning_en = result.warning.en
    conv.evidence = [e.model_dump(mode="json") for e in result.evidence] if result.evidence else None

    per_msg = {m.n: m for m in result.flags_by_message}
    for m in scenario.messages:
        mf = per_msg.get(m.n)
        conv.messages.append(
            MessageRow(
                id=uuid.uuid4(),
                n=m.n,
                author=m.from_.value,
                text=m.text,
                flags=[f.value for f in mf.flags] if mf else [],
                score_after=mf.score_after if mf else 0,
                is_first_alert=result.first_alert == m.n,
            )
        )
    s.flush()

    # EAV: attributes that only some applications have.
    conv_defs = _definitions(s, app.id, "conversation")
    msg_defs = _definitions(s, app.id, "message")
    if scenario.channel.value == "email":
        _set_attr(s, conv_defs, "subject", conv.id, _email_subject(scenario))
    if scenario.audio:
        a = scenario.audio
        _set_attr(s, conv_defs, "audio_id", conv.id, a.audio_id)
        _set_attr(s, conv_defs, "audio_mime", conv.id, a.mime)
        _set_attr(s, conv_defs, "audio_duration_s", conv.id, a.duration_s)
        if a.location:
            _set_attr(s, conv_defs, "voice_region", conv.id, a.location.region)
            _set_attr(s, conv_defs, "voice_confidence", conv.id, a.location.confidence)
    by_n = {row.n: row for row in conv.messages}
    for m in scenario.messages:
        _set_attr(s, msg_defs, "start_s", by_n[m.n].id, m.start_s)
        _set_attr(s, msg_defs, "end_s", by_n[m.n].id, m.end_s)
    s.flush()
    return conv.id


# ---------------------------------------------------------------------------------------------
# Users & auth (minimalist match on username + password)
# ---------------------------------------------------------------------------------------------


def _user_dto(u: User) -> UserInfo:
    return UserInfo(id=u.id, username=u.username, role=u.role, display_name=u.display_name)  # type: ignore[arg-type]


def authenticate_user(s: Session, username: str, password: str) -> UserInfo | None:
    u = s.scalars(select(User).where(User.username == username, User.password == password)).first()
    return _user_dto(u) if u else None


def get_user(s: Session, user_id: uuid.UUID) -> UserInfo | None:
    u = s.get(User, user_id)
    return _user_dto(u) if u else None


def create_user(s: Session, username: str, password: str, display_name: str | None = None) -> UserInfo | None:
    if s.scalars(select(User).where(User.username == username)).first() is not None:
        return None
    u = User(
        id=uuid.uuid4(),
        username=username,
        password=password,
        role="user",
        display_name=(display_name or username).strip() or username,
    )
    s.add(u)
    s.flush()
    return _user_dto(u)


def list_accounts(s: Session) -> list[AccountPreview]:
    rows = s.scalars(select(User).order_by(User.role, User.username))
    return [AccountPreview(username=u.username, role=u.role, display_name=u.display_name) for u in rows]  # type: ignore[arg-type]


def admin_has_conversations(s: Session) -> bool:
    aid = user_uuid("admin")
    return s.scalars(select(Conversation.id).where(Conversation.client_id == aid).limit(1)).first() is not None


# ---------------------------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------------------------


def _summary(c: Conversation, app_code: str, message_count: int, owner: User | None = None) -> dict:
    return dict(
        id=c.id,
        application=app_code,
        contact_id=c.contact_id,
        external_id=c.external_id,
        created_at=c.created_at,
        updated_at=c.updated_at,
        expires_at=c.expires_at,
        verdict=c.verdict,
        scam_type=c.scam_type,
        risk_score=c.risk_score,
        first_alert=c.first_alert,
        message_count=message_count,
        owner_username=owner.username if owner else None,
        owner_role=owner.role if owner else None,
    )


def list_applications(s: Session, client_id: uuid.UUID | None) -> list[ApplicationSummary]:
    purge_expired(s)
    conv_q = select(
        Conversation.application_id.label("app_id"),
        func.count(Conversation.id).label("conversations"),
        func.sum(case((Conversation.verdict == "SCAM", 1), else_=0)).label("scams"),
    )
    contact_q = select(Contact.application_id.label("app_id"), func.count(Contact.id).label("contacts"))
    if client_id is not None:
        conv_q = conv_q.where(Conversation.client_id == client_id)
        contact_q = contact_q.where(Contact.client_id == client_id)
    conv_stats = conv_q.group_by(Conversation.application_id).subquery()
    contact_stats = contact_q.group_by(Contact.application_id).subquery()
    rows = s.execute(
        select(Application, contact_stats.c.contacts, conv_stats.c.conversations, conv_stats.c.scams)
        .outerjoin(contact_stats, contact_stats.c.app_id == Application.id)
        .outerjoin(conv_stats, conv_stats.c.app_id == Application.id)
        .order_by(Application.id)
    )
    return [
        ApplicationSummary(
            code=a.code,
            display_name=a.display_name,
            view_kind=a.view_kind,
            contacts=contacts or 0,
            conversations=convs or 0,
            scams=int(scams or 0),
        )
        for a, contacts, convs, scams in rows
    ]


def list_contacts(s: Session, client_id: uuid.UUID | None, app_code: str) -> list[ContactSummary]:
    purge_expired(s)
    q = (
        select(Contact)
        .join(Application)
        .options(selectinload(Contact.conversations))
        .where(Application.code == app_code)
    )
    if client_id is not None:
        q = q.where(Contact.client_id == client_id)
    contacts = s.scalars(q).all()
    out = []
    for c in contacts:
        last = max(c.conversations, key=lambda x: x.updated_at, default=None)
        out.append(
            ContactSummary(
                id=c.id,
                application=app_code,
                address=c.address,
                display_name=c.display_name,
                known_contact=c.known_contact,
                conversations=len(c.conversations),
                last_verdict=last.verdict if last else None,
                last_risk_score=last.risk_score if last else None,
                last_updated=last.updated_at if last else None,
            )
        )
    out.sort(key=lambda x: (x.last_updated is None, -(x.last_updated.timestamp() if x.last_updated else 0)))
    return out


def list_conversations(s: Session, client_id: uuid.UUID | None, contact_id: uuid.UUID) -> list[ConversationSummary] | None:
    purge_expired(s)
    q = select(Contact).options(selectinload(Contact.application)).where(Contact.id == contact_id)
    if client_id is not None:
        q = q.where(Contact.client_id == client_id)
    contact = s.scalars(q).first()
    if contact is None:
        return None
    owner = s.get(User, contact.client_id)
    rows = s.execute(
        select(Conversation, func.count(MessageRow.id))
        .outerjoin(MessageRow)
        .where(Conversation.contact_id == contact.id)
        .group_by(Conversation.id)
        .order_by(Conversation.external_id)
    )
    return [ConversationSummary(**_summary(c, contact.application.code, n, owner)) for c, n in rows]


def _to_detail(
    c: Conversation, attrs: dict[uuid.UUID, dict[str, Any]], owner: User | None
) -> ConversationDetail:
    conv_attrs = attrs[c.id]
    messages = []
    for m in c.messages:
        msg: dict[str, Any] = {"n": m.n, "from": m.author, "text": m.text}
        for k in ("start_s", "end_s"):
            if attrs[m.id].get(k) is not None:
                msg[k] = attrs[m.id][k]
        messages.append(msg)
    scenario: dict[str, Any] = {
        "id": c.external_id,
        "channel": c.application.code,
        "sender": {
            "name": c.contact.display_name or None,
            "address": c.contact.address or None,
            "known_contact": c.contact.known_contact,
        },
        "messages": messages,
    }
    if conv_attrs.get("audio_id"):
        scenario["audio"] = {
            "audio_id": conv_attrs["audio_id"],
            "mime": conv_attrs.get("audio_mime") or "audio/wav",
            "duration_s": conv_attrs.get("audio_duration_s") or 0,
        }
        if conv_attrs.get("voice_region"):
            scenario["audio"]["location"] = {
                "region": conv_attrs["voice_region"],
                "confidence": conv_attrs.get("voice_confidence") or 0,
            }

    result = AnalysisResult.model_validate(
        {
            "id": c.external_id,
            "verdict": c.verdict,
            "scam_type": c.scam_type,
            "risk_score": c.risk_score,
            "first_alert": c.first_alert,
            "red_flags": c.red_flags,
            "flags_by_message": [{"n": m.n, "flags": m.flags, "score_after": m.score_after} for m in c.messages],
            "warning": {"ro": c.warning_ro, "en": c.warning_en},
            "evidence": c.evidence,
        }
    )
    return ConversationDetail(
        **_summary(c, c.application.code, len(c.messages), owner),
        scenario=Scenario.model_validate(scenario),
        result=result,
        attributes=conv_attrs,
    )


def load_conversation(s: Session, client_id: uuid.UUID | None, conv_id: uuid.UUID) -> ConversationDetail | None:
    q = (
        select(Conversation)
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.contact),
            selectinload(Conversation.application),
        )
        .where(Conversation.id == conv_id)
    )
    if client_id is not None:
        q = q.where(Conversation.client_id == client_id)
    c = s.scalars(q).first()
    if c is None:
        return None
    attrs = _get_attrs(s, [c.id, *(m.id for m in c.messages)])
    owner = s.get(User, c.client_id)
    return _to_detail(c, attrs, owner)


def list_saved_conversations(s: Session, client_id: uuid.UUID | None) -> list[ConversationDetail]:
    """List saved conversations visible to this user (or across all tenants when client_id is None)."""
    purge_expired(s)
    q = (
        select(Conversation)
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.contact),
            selectinload(Conversation.application),
        )
        .order_by(Conversation.updated_at.desc(), Conversation.external_id)
    )
    if client_id is not None:
        q = q.where(Conversation.client_id == client_id)
    convs = s.scalars(q).all()
    if not convs:
        return []
    entity_ids = [x for c in convs for x in (c.id, *(m.id for m in c.messages))]
    attrs = _get_attrs(s, entity_ids)
    owner_ids = {c.client_id for c in convs}
    owners = {u.id: u for u in s.scalars(select(User).where(User.id.in_(owner_ids)))}
    return [_to_detail(c, attrs, owners.get(c.client_id)) for c in convs]


# ---------------------------------------------------------------------------------------------
# Delete (privacy: user-initiated + expiry)
# ---------------------------------------------------------------------------------------------


def _delete_conversations(s: Session, where) -> int:
    convs = s.scalars(select(Conversation).options(selectinload(Conversation.messages)).where(where)).all()
    _delete_attrs(s, [x for c in convs for x in (c.id, *(m.id for m in c.messages))])
    for c in convs:
        s.delete(c)
    s.flush()
    return len(convs)


def _delete_orphan_contacts(s: Session) -> None:
    orphan = select(Contact.id).where(~select(Conversation.id).where(Conversation.contact_id == Contact.id).exists())
    ids = list(s.scalars(orphan))
    _delete_attrs(s, ids)
    if ids:
        s.execute(delete(Contact).where(Contact.id.in_(ids)))


def delete_conversation(s: Session, client_id: uuid.UUID | None, conv_id: uuid.UUID) -> int:
    where = Conversation.id == conv_id
    if client_id is not None:
        where = where & (Conversation.client_id == client_id)
    n = _delete_conversations(s, where)
    _delete_orphan_contacts(s)
    return n


def delete_contact(s: Session, client_id: uuid.UUID | None, contact_id: uuid.UUID) -> int:
    where = Conversation.contact_id == contact_id
    if client_id is not None:
        where = where & (Conversation.client_id == client_id)
    n = _delete_conversations(s, where)
    _delete_orphan_contacts(s)
    return n


def delete_all(s: Session, client_id: uuid.UUID | None) -> int:
    where = True if client_id is None else (Conversation.client_id == client_id)
    n = _delete_conversations(s, where)
    _delete_orphan_contacts(s)
    return n


def purge_expired(s: Session) -> int:
    n = _delete_conversations(s, Conversation.expires_at < datetime.now(UTC))
    if n:
        _delete_orphan_contacts(s)
    return n
