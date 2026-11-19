"""The single place that decides whether a conversation is stored: only when `opts.save` is true
(the user ticked the consent checkbox). Without consent the DB is never touched."""

import uuid

from fastapi import HTTPException

from app.db.repository import save_conversation
from app.db.session import Database
from app.detector.client import DetectorClient
from app.schemas import AnalyzeResponse, SaveOptions, Scenario


def analyze_and_maybe_save(
    detector: DetectorClient, db: Database, scenarios: list[Scenario], opts: SaveOptions
) -> list[AnalyzeResponse]:
    results = [detector.analyze(sc) for sc in scenarios]
    if not opts.save:
        return [AnalyzeResponse(result=r) for r in results]

    if not db.ready and not db.ping():
        raise HTTPException(503, "Nu am putut salva: baza de date nu este disponibilă. Analiza funcționează fără salvare.")
    client_id = opts.client_id or uuid.uuid4()
    with db.sessionmaker.begin() as s:
        ids = [save_conversation(s, client_id, sc, r, opts.retention_hours) for sc, r in zip(scenarios, results)]
    return [
        AnalyzeResponse(result=r, saved=True, conversation_id=cid, client_id=client_id)
        for r, cid in zip(results, ids)
    ]
