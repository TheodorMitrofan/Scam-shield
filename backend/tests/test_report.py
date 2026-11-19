import json
import logging
import smtplib

import pytest
from sqlalchemy import func, select

from app.api import report as report_api
from app.config import get_settings
from app.db.models import Contact, Conversation
from app.report import REPORT_RECIPIENT
from app.report.indicators import defang, defang_text

from .conftest import SCENARIOS

PERSON = {"last_name": "Popescu", "first_name": "Maria", "phone": "0722 000 000",
          "cnp": "2500101123456", "lost_money": True, "amount_lost": 1850, "bank": "Banca Dunărea"}


class FakeSMTP:
    instances: list["FakeSMTP"] = []
    fail_auth = False

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.calls, self.sent = host, port, [], []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, pw):
        if FakeSMTP.fail_auth == "disconnect":
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        if FakeSMTP.fail_auth:
            raise smtplib.SMTPAuthenticationError(535, b"bad")
        self.calls.append(("login", user))

    def send_message(self, msg):
        self.sent.append(msg)


@pytest.fixture(autouse=True)
def smtp(monkeypatch):
    FakeSMTP.instances, FakeSMTP.fail_auth = [], False
    monkeypatch.setattr("app.report.mailer.smtplib.SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_USER", "sender@test.local")  # env beats any local backend/.env
    monkeypatch.setenv("SMTP_PASSWORD", "test-app-password")
    get_settings.cache_clear()
    report_api._sent.clear()
    yield FakeSMTP
    get_settings.cache_clear()


def draft(client, key):
    r = client.post("/api/report/draft", json={"scenario": SCENARIOS[key]})
    assert r.status_code == 200, r.text
    return r.json()


def test_draft_generated_part_and_empty_personal_data(client):
    d = draft(client, "V04")
    inc = d["incident"]
    assert d["recipient"] == REPORT_RECIPIENT == "francescomartinut18@gmail.com"
    assert inc["risk_score"] == 80 and inc["first_alert"] == 5 and inc["scam_type"] == "FAMILY_EMERGENCY"
    assert "WhatsApp" in inc["summary_ro"] and "mesajul 5" in inc["summary_ro"]
    assert [t["is_first_alert"] for t in inc["timeline"]].index(True) == 4
    assert {i["display"] for i in inc["indicators"]} >= {"+40 7xx xxx 318", "1.850 lei"}
    assert all(v in (None, False) for v in d["personal_data"].values())
    keys = [f["key"] for f in d["personal_fields"]]
    assert keys[:2] == ["last_name", "first_name"] and "cnp" in keys


@pytest.mark.parametrize("key,expected", [
    ("V01", "bancadunarea-securitate[.]com"),
    ("V06", "notificari[@]anaf-rambursari[.]net"),
    ("V08", "piatamea-plati[.]com"),
])
def test_indicators_are_defanged(client, key, expected):
    d = draft(client, key)
    displays = [i["display"] for i in d["incident"]["indicators"]]
    assert expected in displays
    raw = expected.replace("[.]", ".").replace("[@]", "@")
    assert raw not in d["incident"]["summary_ro"]  # never a clickable link in the generated text


@pytest.mark.parametrize("key", ["V03", "V05", "V09"])  # SAFE, SAFE, SUSPICIOUS(35)
def test_no_report_below_50(client, key):
    r = client.post("/api/report/draft", json={"scenario": SCENARIOS[key]})
    assert r.status_code == 422 and "50" in r.json()["detail"]


def test_send_emails_demo_inbox(client, smtp):
    d = draft(client, "V01")
    r = client.post("/api/report/send", json={"report": d, "personal_data": PERSON})
    assert r.status_code == 200, r.text
    assert r.json()["sent"] and r.json()["recipient"] == "francescomartinut18@gmail.com"
    s = smtp.instances[0]
    assert (s.host, s.port) == ("smtp.gmail.com", 587)
    assert s.calls == ["starttls", ("login", "sender@test.local")]
    msg = s.sent[0]
    assert msg["To"] == "francescomartinut18@gmail.com" and msg["From"] == "sender@test.local"
    assert "DEMO" in msg["Subject"]
    body = msg.get_body(("plain",)).get_content()
    assert "Popescu Maria" in body and "2500101123456" in body and "bancadunarea-securitate[.]com" in body
    assert "bancadunarea-securitate.com" not in body
    atts = {a.get_filename(): a for a in msg.iter_attachments()}
    assert set(atts) == {"sesizare.pdf", "raport.json"}
    assert atts["sesizare.pdf"].get_content().startswith(b"%PDF")
    payload = json.loads(atts["raport.json"].get_content())
    assert payload["personal_data"]["last_name"] == "Popescu"


def test_recipient_cannot_be_overridden_by_client(client, smtp):
    d = draft(client, "V01")
    d["recipient"] = "alerts@dnsc.ro"
    client.post("/api/report/send", json={"report": d, "personal_data": PERSON})
    assert smtp.instances[0].sent[0]["To"] == "francescomartinut18@gmail.com"


@pytest.mark.parametrize("person", [
    {"first_name": "Maria", "phone": "0722"},              # no last name
    {"last_name": "Popescu", "first_name": "Maria"},       # no contact
    {**PERSON, "cnp": "123"},                              # bad CNP
    {**PERSON, "email": "nu-e-email"},                     # bad e-mail
])
def test_send_validation(client, smtp, person):
    d = draft(client, "V01")
    r = client.post("/api/report/send", json={"report": d, "personal_data": person})
    assert r.status_code == 422 and not smtp.instances


def test_send_twice_is_409(client):
    d = draft(client, "V07")
    assert client.post("/api/report/send", json={"report": d, "personal_data": PERSON}).status_code == 200
    assert client.post("/api/report/send", json={"report": d, "personal_data": PERSON}).status_code == 409


def test_not_configured_is_503(client, smtp, monkeypatch):
    monkeypatch.setenv("SMTP_PASSWORD", "")
    get_settings.cache_clear()
    d = draft(client, "V01")
    assert client.post("/api/report/send", json={"report": d, "personal_data": PERSON}).status_code == 503
    assert not smtp.instances


def test_bad_password_is_502_and_can_retry(client, smtp):
    d = draft(client, "V01")
    smtp.fail_auth = True
    r = client.post("/api/report/send", json={"report": d, "personal_data": PERSON})
    assert r.status_code == 502 and "parolă de aplicație" in r.json()["detail"]
    smtp.fail_auth = False
    assert client.post("/api/report/send", json={"report": d, "personal_data": PERSON}).status_code == 200


def test_nothing_stored_and_nothing_personal_logged(client, db, caplog):
    caplog.set_level(logging.DEBUG)  # needs the logging plugin (default pytest run)
    d = draft(client, "V11")
    client.post("/api/report/send", json={"report": d, "personal_data": PERSON})
    with db.sessionmaker() as s:
        assert s.scalar(select(func.count()).select_from(Conversation)) == 0
        assert s.scalar(select(func.count()).select_from(Contact)) == 0
    assert "Popescu" not in caplog.text and "2500101123456" not in caplog.text


@pytest.mark.parametrize("text", ["", "😀😀😀", "a" * 15000])
def test_robust_inputs(client, text):
    sc = {"id": "X", "channel": "sms", "sender": {"name": None, "address": None, "known_contact": False},
          "messages": [{"n": 1, "from": "sender", "text": text}]}
    res = {"id": "X", "verdict": "SCAM", "scam_type": "OTHER", "risk_score": 60, "first_alert": 1,
           "red_flags": ["RF_CODE_REQUEST", "RF_URGENCY"], "warning": {"ro": "x"}}
    r = client.post("/api/report/draft", json={"scenario": sc, "result": res})
    assert r.status_code == 200
    assert client.post("/api/report/pdf", json={"report": r.json()}).status_code == 200


def test_defang_examples():
    assert defang("https://a.b.com/x") == "hxxps://a[.]b[.]com/x"
    assert defang("x@y.net") == "x[@]y[.]net"
    assert defang_text("Accesați: a-b.com/x. Scrieți la x@y.ro!") == "Accesați: a-b[.]com/x. Scrieți la x[@]y[.]ro!"
    assert defang_text("Ramburs 1.276 lei, dvs. azi") == "Ramburs 1.276 lei, dvs. azi"


def test_pdf_download_blank_and_filled(client):
    d = draft(client, "V04")
    blank = client.post("/api/report/pdf", json={"report": d})
    filled = client.post("/api/report/pdf", json={"report": d, "personal_data": PERSON})
    for r in (blank, filled):
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF") and len(r.content) > 5000
    assert 'filename="sesizare-V04.pdf"' in blank.headers["content-disposition"]


def test_pdf_handles_every_validation_scam(client):
    for key in SCENARIOS:
        r = client.post("/api/report/draft", json={"scenario": SCENARIOS[key]})
        if r.status_code == 200:
            assert client.post("/api/report/pdf", json={"report": r.json()}).status_code == 200


def test_gmail_closing_connection_on_login_means_bad_password(client, smtp):
    d = draft(client, "V01")
    smtp.fail_auth = "disconnect"
    r = client.post("/api/report/send", json={"report": d, "personal_data": PERSON})
    assert r.status_code == 502 and "parolă de aplicație" in r.json()["detail"]
