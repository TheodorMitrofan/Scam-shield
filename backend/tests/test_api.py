import uuid

from sqlalchemy import func, select

from app.db.models import AttributeValue, Contact, Conversation, MessageRow

from .conftest import EXPECTED, SCENARIOS


def count(db, model) -> int:
    with db.sessionmaker() as s:
        return s.scalar(select(func.count()).select_from(model))


def test_health(client):
    r = client.get("/api/health").json()
    assert r == {"status": "ok", "model_loaded": True, "detector_stub": False, "db_connected": True}


def test_validation_endpoint(client):
    ids = [s["id"] for s in client.get("/api/scenarios/validation").json()]
    assert ids == sorted(SCENARIOS)


def test_without_consent_nothing_is_stored(client, db, cid):
    r = client.post("/api/analyze", json=SCENARIOS["V04"], headers=cid).json()
    assert r["saved"] is False and r["conversation_id"] is None
    assert r["result"]["verdict"] == "SCAM" and r["result"]["risk_score"] == 80
    client.post("/api/analyze/batch", json=list(SCENARIOS.values()))
    client.post("/api/analyze/text", json={"text": "Cardul a fost blocat"})
    assert count(db, Conversation) == count(db, Contact) == count(db, MessageRow) == 0


def test_batch_matches_answer_key_sorted(client):
    rows = client.post("/api/analyze/batch", json=list(reversed(SCENARIOS.values()))).json()
    assert [r["result"]["id"] for r in rows] == sorted(SCENARIOS)
    for r in rows:
        exp = EXPECTED[r["result"]["id"]]
        assert (r["result"]["verdict"], r["result"]["risk_score"]) == (exp["verdict"], int(exp["risk_score"]))


def test_save_builds_hierarchy_and_roundtrips(client, db, cid):
    rows = client.post("/api/analyze/batch?save=true", json=list(SCENARIOS.values()), headers=cid).json()
    assert all(r["saved"] and r["client_id"] == cid["X-Client-Id"] for r in rows)
    assert count(db, Conversation) == 11
    assert count(db, MessageRow) == sum(len(s["messages"]) for s in SCENARIOS.values())

    apps = {a["code"]: a for a in client.get("/api/apps", headers=cid).json()}
    assert apps["sms"]["conversations"] == 5 and apps["whatsapp"]["conversations"] == 2
    assert apps["email"]["scams"] == 1 and apps["call_transcript"]["conversations"] == 2

    contacts = client.get("/api/apps/whatsapp/contacts", headers=cid).json()
    assert {c["display_name"] for c in contacts} == {None, "Maria (vecina)"}
    v04 = next(c for c in contacts if c["address"] == "+40 7xx xxx 318")
    convs = client.get(f"/api/contacts/{v04['id']}/conversations", headers=cid).json()
    assert [c["external_id"] for c in convs] == ["V04"] and convs[0]["message_count"] == 6

    detail = client.get(f"/api/conversations/{convs[0]['id']}", headers=cid).json()
    assert detail["scenario"] == SCENARIOS["V04"]  # exact original conversation back
    assert detail["result"]["first_alert"] == 5 and detail["result"]["flags_by_message"][4]["flags"]


def test_same_contact_groups_conversations(client, cid):
    # V01 and V03 are both from "BancaDunarea" on SMS → one contact, two conversations.
    for k in ("V01", "V03"):
        client.post("/api/analyze?save=true", json=SCENARIOS[k], headers=cid)
    bank = [c for c in client.get("/api/apps/sms/contacts", headers=cid).json() if c["address"] == "BancaDunarea"]
    assert len(bank) == 1 and bank[0]["conversations"] == 2


def test_resave_replaces_instead_of_duplicating(client, db, cid):
    for _ in range(3):
        client.post("/api/analyze?save=true", json=SCENARIOS["V07"], headers=cid)
    assert count(db, Conversation) == 1 and count(db, MessageRow) == 5


def test_email_subject_is_eav_attribute(client, cid):
    r = client.post("/api/analyze?save=true", json=SCENARIOS["V06"], headers=cid).json()
    d = client.get(f"/api/conversations/{r['conversation_id']}", headers=cid).json()
    assert d["attributes"]["subject"].startswith("Stimate contribuabil")


def test_audio_timestamps_and_location_roundtrip(client, cid):
    sc = {**SCENARIOS["V07"], "id": "A01"}
    sc["messages"] = [{**m, "start_s": i * 3.0, "end_s": i * 3.0 + 2.5} for i, m in enumerate(sc["messages"])]
    sc["audio"] = {"audio_id": "abc", "mime": "audio/wav", "duration_s": 15.0,
                   "location": {"region": "Moldova", "confidence": 0.7}}
    r = client.post("/api/analyze?save=true", json=sc, headers=cid).json()
    d = client.get(f"/api/conversations/{r['conversation_id']}", headers=cid).json()
    assert d["scenario"] == sc and d["attributes"]["voice_region"] == "Moldova"


def test_clients_are_isolated(client, cid):
    r = client.post("/api/analyze?save=true", json=SCENARIOS["V02"], headers=cid).json()
    other = {"X-Client-Id": str(uuid.uuid4())}
    assert client.get(f"/api/conversations/{r['conversation_id']}", headers=other).status_code == 404
    assert all(a["conversations"] == 0 for a in client.get("/api/apps", headers=other).json())
    assert client.delete("/api/history", headers=other).json() == {"deleted": 0}


def test_consent_without_client_id_generates_one(client):
    r = client.post("/api/analyze/text?save=true", json={"text": "Felicitări, ați câștigat!"}).json()
    assert r["saved"] and uuid.UUID(r["client_id"])


def test_delete_removes_everything_including_eav(client, db, cid):
    client.post("/api/analyze/batch?save=true", json=list(SCENARIOS.values()), headers=cid)
    assert count(db, AttributeValue) > 0
    assert client.delete("/api/history", headers=cid).json() == {"deleted": 11}
    assert count(db, Conversation) == count(db, Contact) == count(db, MessageRow) == count(db, AttributeValue) == 0


def test_history_requires_client_id(client):
    assert client.get("/api/apps").status_code == 400


def test_save_with_db_down_returns_503_but_analysis_works(cid):
    from fastapi.testclient import TestClient

    from app.db.session import Database
    from app.detector.client import DetectorClient
    from app.main import create_app

    from .conftest import AnswerKeyDetector

    down = Database("postgresql+psycopg://x:x@127.0.0.1:1/none")
    with TestClient(create_app(db=down, detector=DetectorClient(AnswerKeyDetector()))) as c:
        assert c.post("/api/analyze", json=SCENARIOS["V01"]).status_code == 200
        assert c.post("/api/analyze?save=true", json=SCENARIOS["V01"], headers=cid).status_code == 503
