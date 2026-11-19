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

_KIND_LABEL = {"url": "Adresă de internet", "email": "Adresă de e-mail", "phone": "Număr de telefon",
               "iban": "Cont bancar (IBAN)", "amount": "Sumă menționată"}


def _v(x) -> str:
    return str(x) if x not in (None, "") else "—"


def render_text(draft: FraudReportDraft, p: PersonalData) -> str:
    inc = draft.incident
    lines = [
        "SESIZARE PRIVIND O TENTATIVĂ DE ÎNȘELĂCIUNE",
        "(raport generat automat de Scam Shield — DEMO hackathon, nu a fost trimis autorităților)",
        "",
        "1. DATELE PETENTULUI",
        f"   Nume și prenume: {_v(p.last_name)} {_v(p.first_name)}",
        f"   CNP: {_v(p.cnp)}",
        f"   Act de identitate (serie, număr): {_v(p.id_series_number)}",
        f"   Domiciliu: {_v(p.address)}",
        f"   Telefon: {_v(p.phone)}",
        f"   E-mail: {_v(p.email)}",
        "",
        "2. DESCRIEREA FAPTEI",
        f"   Data incidentului: {p.incident_date.strftime('%d.%m.%Y') if p.incident_date else 'nespecificată'}",
        f"   Canal: {inc.channel_label}",
        f"   Tip: {inc.scam_type_label} (scor de risc {inc.risk_score}/100)",
        f"   {inc.summary_ro}",
        "",
        "3. EXPEDITORUL SUSPECT",
        f"   Nume afișat: {_v(defang_text(inc.sender.name or ''))}",
        f"   Număr / adresă: {_v(defang_text(inc.sender.address or ''))}",
        f"   În agenda mea: {'da' if inc.sender.known_contact else 'nu'}",
        "",
        "4. CONVERSAȚIA (mesajele numerotate)",
    ]
    for t in inc.timeline:
        mark = "  <-- aici a început tentativa" if t.is_first_alert else ""
        lines.append(f"   [{t.n}] {t.author_label}: {t.text}{mark}")
    lines += ["", "5. ELEMENTE DE IDENTIFICARE (scrise dezactivat, nu le accesați)"]
    if inc.indicators:
        lines += [f"   - {_KIND_LABEL[i.kind]}: {i.display}" for i in inc.indicators]
    else:
        lines.append("   —")
    lines += ["", "6. SEMNALE DE ÎNȘELĂCIUNE DETECTATE"]
    lines += [f"   - Persoana {f.label} ({f.code.value})" for f in inc.red_flags] or ["   —"]
    lines += [
        "",
        "7. PREJUDICIU",
        f"   Am pierdut bani: {'da' if p.lost_money else 'nu'}",
        f"   Suma: {_v(p.amount_lost)}{' lei' if p.amount_lost is not None else ''}",
        f"   Banca: {_v(p.bank)}",
        "",
        "8. ALTE DETALII",
        f"   {_v(p.additional_details)}",
        "",
        f"Raport nr. {draft.report_id} · generat la {draft.generated_at.strftime('%d.%m.%Y %H:%M')} UTC",
    ]
    return "\n".join(lines)


def render_email(draft: FraudReportDraft, personal: PersonalData, sender: str) -> EmailMessage:
    now = datetime.now(UTC)
    msg = EmailMessage()
    msg["Subject"] = (
        f"[Scam Shield – DEMO] Sesizare tentativă de fraudă – {draft.incident.scam_type_label} – "
        f"{draft.incident.channel_label} – {now.strftime('%d.%m.%Y')}"
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
