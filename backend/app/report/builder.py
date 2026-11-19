"""Builds the fraud report: the generated incident (draft) and the final e-mail."""

import json
import uuid
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

from app.schemas import AnalysisResult, Scenario
from app.schemas.report import (
    FlagExplanation,
    FraudReportDraft,
    Incident,
    PersonalData,
    SuspectSender,
    TimelineEntry,
)

from . import REPORT_RECIPIENT
from .indicators import defang_text, extract_indicators
from .pdf import render_pdf
from .labels import CHANNEL_LABEL, CHANNEL_PHRASE, FLAG_LABEL, SCAM_TYPE_LABEL, SCAM_TYPE_STORY


def _sender_phrase(scenario: Scenario) -> str:
    s = scenario.sender
    name, address = defang_text(s.name or ""), defang_text(s.address or "")
    if name and address and s.address != s.name:
        who = f"„{name}” ({address})"
    elif name or address:
        who = f"„{name or address}”"
    else:
        who = "un expeditor necunoscut"
    where = "un contact salvat în agenda mea" if s.known_contact else "care nu se află în agenda mea"
    return f"{who}, {where}"


def _summary(scenario: Scenario, result: AnalysisResult, incident_indicators) -> str:
    sentences = [f"Am primit {CHANNEL_PHRASE[scenario.channel]} de la {_sender_phrase(scenario)}."]
    story = SCAM_TYPE_STORY.get(result.scam_type)
    if story:
        sentences.append(story)
    if result.red_flags:
        sentences.append("Semnale observate: persoana " + "; ".join(FLAG_LABEL[f] for f in result.red_flags) + ".")
    if len(scenario.messages) > 1 and result.first_alert:
        sentences.append(
            f"Conversația are {len(scenario.messages)} mesaje, iar tentativa de înșelăciune "
            f"a devenit evidentă la mesajul {result.first_alert}."
        )
    used = [i.display for i in incident_indicators if i.message_n is not None and i.kind in ("url", "email", "phone", "iban")]
    if used:
        sentences.append("Elemente folosite de expeditor: " + ", ".join(used) + ".")
    return " ".join(sentences)


def build_draft(scenario: Scenario, result: AnalysisResult) -> FraudReportDraft:
    flags_at = {m.n: m.flags for m in result.flags_by_message}
    indicators = extract_indicators(scenario)
    timeline = [
        TimelineEntry(
            n=m.n,
            author=m.from_.value,
            author_label="Eu" if m.from_.value == "reader" else "Expeditorul",
            text=defang_text(m.text),
            is_first_alert=result.first_alert == m.n,
            flags=flags_at.get(m.n, []),
        )
        for m in scenario.messages
    ]
    incident = Incident(
        scenario_id=scenario.id,
        channel=scenario.channel,
        channel_label=CHANNEL_LABEL[scenario.channel],
        sender=SuspectSender(**scenario.sender.model_dump()),
        verdict=result.verdict,
        scam_type=result.scam_type,
        scam_type_label=SCAM_TYPE_LABEL[result.scam_type],
        risk_score=result.risk_score,
        first_alert=result.first_alert,
        red_flags=[FlagExplanation(code=f, label=FLAG_LABEL[f]) for f in result.red_flags],
        summary_ro=_summary(scenario, result, indicators),
        timeline=timeline,
        indicators=indicators,
    )
    return FraudReportDraft(
        report_id=uuid.uuid4(),
        generated_at=datetime.now(UTC),
        recipient=REPORT_RECIPIENT,
        incident=incident,
    )


# ---------------------------------------------------------------------------------------------
# E-mail
# ---------------------------------------------------------------------------------------------



def render_text(draft: FraudReportDraft, p: PersonalData) -> str:
    """Short, formal cover letter; the complaint itself is the attached PDF."""
    name = f"{p.last_name or ''} {p.first_name or ''}".strip()
    contact = ", ".join(x for x in (p.phone, p.email) if x)
    when = p.incident_date.strftime("%d.%m.%Y") if p.incident_date else "nespecificată"
    return "\n".join([
        "Bună ziua,",
        "",
        f"Subsemnatul/a {name} vă transmit, atașat, o plângere penală privind o tentativă de înșelăciune "
        f"prin {draft.incident.channel_label}, din data de {when}.",
        "",
        "Plângerea (sesizare.pdf) cuprinde datele mele de identificare, starea de fapt și, în Anexa 1, "
        "transcrierea integrală a conversației.",
        "",
        f"Mă puteți contacta la: {contact}.",
        "",
        "Cu respect,",
        name,
        "",
        "—",
        "Mesaj generat cu Scam Shield (demonstrație hackathon). Nu a fost transmis autorităților.",
    ])


def render_email(draft: FraudReportDraft, personal: PersonalData, sender: str) -> EmailMessage:
    now = datetime.now(UTC)
    msg = EmailMessage()
    name = f"{personal.last_name or ''} {personal.first_name or ''}".strip()
    msg["Subject"] = (
        f"[DEMO] Plângere penală – tentativă de înșelăciune prin {draft.incident.channel_label} – "
        f"{name} – {now.strftime('%d.%m.%Y')}"
    )
    msg["From"] = sender
    msg["To"] = REPORT_RECIPIENT  # HACK: demo only — hardcoded, never real authorities
    if personal.email:
        msg["Reply-To"] = personal.email
    msg["Date"] = format_datetime(now)
    msg["Message-ID"] = make_msgid(domain="scamshield.local")
    msg.set_content(render_text(draft, personal))
    payload = {
        "report": draft.model_dump(mode="json", exclude={"personal_fields", "personal_data"}),
        "personal_data": personal.model_dump(mode="json"),
    }
    msg.add_attachment(render_pdf(draft, personal), maintype="application", subtype="pdf", filename="sesizare.pdf")
    msg.add_attachment(
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        maintype="application",
        subtype="json",
        filename="raport.json",
    )
    return msg
