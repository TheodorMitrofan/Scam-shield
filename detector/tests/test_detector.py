"""pytest detector/tests  (SCAM_RULES_ONLY=1 to skip the model)"""
import csv
import json
import re
from pathlib import Path

import pytest

import scam_detector as sd

ROOT = Path(__file__).resolve().parents[2]
VAL = ROOT / "Scam_Shield_Public_Kit" / "validation_set"
EXP = ROOT / "Scam_Shield_Public_Kit" / "validation_expected_results.csv"
WINDOWS = {"V11": (3, 5)}


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.skipif(not EXP.exists(), reason="kit missing")
def test_validation_set_matches_answer_key():
    with open(EXP, encoding="utf-8-sig") as f:
        expected = {r["id"]: r for r in csv.DictReader(f)}
    for path in sorted(VAL.glob("*.json")):
        r = sd.analyze(_load(path))
        e = expected[r["id"]]
        assert r["verdict"] == e["verdict"], r["id"]
        assert r["scam_type"] == e["scam_type"], r["id"]
        if e["first_alert"]:
            lo, hi = WINDOWS.get(r["id"], (int(e["first_alert"]),) * 2)
            assert lo <= r["first_alert"] <= hi, r["id"]
        else:
            assert r["first_alert"] is None


@pytest.mark.parametrize("text", ["", "   ", "😀😀😀🙏", "a" * 20000, "DA", "\n\n\n", "0800 100 200",
                                  "trimite-mi codul " * 500, "Buna ziua, va sun de la banca"])
def test_robust_inputs_do_not_crash(text):
    r = sd.analyze_text(text)
    assert r["verdict"] in {"SAFE", "SUSPICIOUS", "SCAM"}
    assert 0 <= r["risk_score"] <= 100
    assert r["warning"]["ro"]


def test_garbage_scenarios_do_not_crash():
    for s in [{}, {"messages": None}, {"messages": [None, 5, {"text": None}]}, {"id": 3, "sender": None,
                                                                            "messages": [{"n": 1, "text": "x"}]}]:
        r = sd.analyze(s)
        assert r["verdict"] in {"SAFE", "SUSPICIOUS", "SCAM"}


def test_repeatable():
    s = _load(VAL / "V04.json") if VAL.exists() else None
    if s is None:
        pytest.skip()
    a, b = sd.analyze(s), sd.analyze(s)
    assert a == b


def test_no_diacritics_same_result():
    a = sd.analyze_text("Banca Dunărea: Cardul dvs. a fost blocat. Accesați în 24h: bancadunarea-securitate.com")
    b = sd.analyze_text("Banca Dunarea: Cardul dvs. a fost blocat. Accesati in 24h: bancadunarea-securitate.com")
    assert (a["verdict"], a["scam_type"], a["red_flags"]) == (b["verdict"], b["scam_type"], b["red_flags"])


_LINK = re.compile(r"[a-z0-9\-]+\.(?:com|net|info|xyz|top|online|site|co|ro)(?:/\S*)?", re.I)


@pytest.mark.parametrize("path", sorted(VAL.glob("*.json")) if VAL.exists() else [])
def test_warning_never_repeats_message_links_or_numbers(path):
    s = _load(path)
    r = sd.analyze(s)
    w = r["warning"]["ro"]
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", w.strip()) if x]
    assert len(sentences) <= 3, w
    official = {"bancadunarea.ro", "curierexpres.ro", "piatamea.ro", "megashop.ro", "anaf.ro"}
    for m in s["messages"]:
        for link in _LINK.findall(m["text"]):
            if link.lower().split("/")[0] not in official:
                assert link.lower() not in w.lower(), (link, w)


def test_challenge_set_verdicts():
    """Hand-written scenarios that are NOT in the validation set. Reported, not all required."""
    data = _load(Path(__file__).parent / "challenge_set.json")
    bad = []
    for s in data:
        e = s.pop("expected")
        r = sd.analyze(s)
        if r["verdict"] != e["verdict"] or r["scam_type"] != e["scam_type"]:
            bad.append((s["id"], r["verdict"], r["scam_type"], e))
    # no scam may be called SAFE
    missed = [b for b in bad if b[1] == "SAFE" and b[3]["verdict"] != "SAFE"]
    assert not missed, missed


def _sc(sid, channel, sender, *msgs):
    return {"id": sid, "channel": channel, "sender": sender,
            "messages": [{"n": i, "from": f, "text": t} for i, (f, t) in enumerate(msgs, 1)]}


def test_regressions_from_scam_shield_creative_traps():
    """Cases from Francesco's creative traps (origin/model-train) that scam_detector used to get wrong."""
    unknown = {"name": None, "address": "+40 311 000 999", "known_contact": False}
    r = sd.analyze(_sc("ACC", "call_transcript", unknown,
                       ("sender", "Sărut mâna buni! Sunt Vlad... Plâng de nu mai pot!"),
                       ("reader", "Vlăduț? Ce s-a întâmplat maică?"),
                       ("sender", "Am făcut un accident grav cu mașina, am lovit un om pe trecere și sunt la poliție!"),
                       ("reader", "Doamne apără și păzește! Cum adică?"),
                       ("sender", "Avocatul zice că dacă plătim 15.000 lei daune acum scăp de arest! Te rog nu-i spune "
                                  "mamei că moare de inimă! Poți să-mi transferi banii urgent?")))
    assert (r["verdict"], r["scam_type"]) == ("SCAM", "FAMILY_EMERGENCY")
    assert "RF_PAYMENT_REQUEST" in r["red_flags"]

    r = sd.analyze(_sc("DENT", "sms", {"name": "DentalPlus", "address": "DentalPlus", "known_contact": False},
                       ("sender", "Clinica DentalPlus: Vă amintim de programarea la stomatologie de mâine, ora 15:00. "
                                  "Vă rugăm confirmați cu DA sau sunați la 021 999 888.")))
    assert r["verdict"] == "SAFE", r["red_flags"]

    r = sd.analyze(_sc("TG", "chat", {"name": "Client_77", "address": "client_77", "known_contact": False},
                       ("sender", "Nu-mi merge aplicația aici deloc. Hai să continuăm discuția pe Telegram la "
                                  "@invest_crypto_fast ca să facem plata.")))
    assert (r["verdict"], r["scam_type"]) == ("SUSPICIOUS", "INVESTMENT")

    # an unlisted phone still counts when the message claims an organisation
    r = sd.analyze(_sc("BANKPH", "sms", {"name": None, "address": "+40 744 000 111", "known_contact": False},
                       ("sender", "Banca dvs: sunati la 0744 123 456 pentru deblocarea cardului.")))
    assert "RF_SUSPICIOUS_CONTACT" in r["red_flags"]
