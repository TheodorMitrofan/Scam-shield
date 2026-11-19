"""Fraud report controllers.

POST /report/draft — only for SCAM results (risk_score ≥ 50): generated incident + empty personal-data form.
POST /report/send  — the user filled in their data and pressed "Trimite e-mail": send to the demo inbox.
Nothing here touches the database, and personal data is never logged.
"""

import threading
import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.report import REPORT_MIN_SCORE, REPORT_RECIPIENT
from app.report.builder import build_draft, render_email
from app.report.pdf import render_pdf
from app.report.mailer import MailFailed, MailNotConfigured, send_email
from app.schemas.report import (
    FraudReportDraft,
    ReportDraftRequest,
    ReportPdfRequest,
    ReportSendRequest,
    ReportSendResponse,
)

from .deps import Detector

router = APIRouter(prefix="/report", tags=["report"])

_NOT_A_SCAM = "Raportul se generează doar pentru mesajele marcate ca țeapă (scor de risc 50 sau mai mare)."
_DEDUP_SECONDS = 600
_sent: dict[str, float] = {}
_sent_lock = threading.Lock()


@router.post("/draft", response_model=FraudReportDraft)
async def draft(body: ReportDraftRequest, detector: Detector) -> FraudReportDraft:
    result = body.result or await run_in_threadpool(detector.analyze, body.scenario)
    if result.risk_score < REPORT_MIN_SCORE:
        raise HTTPException(422, _NOT_A_SCAM)
    return build_draft(body.scenario, result)


@router.post("/pdf", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
async def pdf(body: ReportPdfRequest) -> Response:
    """Download / preview the „Sesizare” PDF. Personal data optional: empty fields print as dotted lines."""
    if body.report.incident.risk_score < REPORT_MIN_SCORE:
        raise HTTPException(422, _NOT_A_SCAM)
    data = await run_in_threadpool(render_pdf, body.report, body.personal_data)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="sesizare-{body.report.incident.scenario_id}.pdf"'},
    )


@router.post("/send", response_model=ReportSendResponse)
async def send(body: ReportSendRequest) -> ReportSendResponse:
    if body.report.incident.risk_score < REPORT_MIN_SCORE:
        raise HTTPException(422, _NOT_A_SCAM)
    settings = get_settings()
    key = str(body.report.report_id)
    now = time.monotonic()
    with _sent_lock:
        for k in [k for k, t in _sent.items() if now - t > _DEDUP_SECONDS]:
            _sent.pop(k)
        if key in _sent:
            raise HTTPException(409, "Raportul a fost deja trimis.")
        _sent[key] = now  # reserve, released again on failure

    msg = render_email(body.report, body.personal_data, sender=settings.smtp_user)
    try:
        await run_in_threadpool(send_email, msg, settings)
    except MailNotConfigured:
        _release(key)
        raise HTTPException(503, "Trimiterea e-mailului nu este configurată pe server.")
    except MailFailed as e:
        _release(key)
        raise HTTPException(502, str(e))
    return ReportSendResponse(
        sent=True, recipient=REPORT_RECIPIENT, message_id=msg["Message-ID"], sent_at=datetime.now(UTC)
    )


def _release(key: str) -> None:
    with _sent_lock:
        _sent.pop(key, None)
