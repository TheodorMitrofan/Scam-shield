"""Combine rules + contact checks + (optional) model into the official result format."""
import re

from . import contacts as C
from . import rules as R
from .catalog import FLAG_ORDER, get_catalog
from .normalize import compact, norm

# Flags the model is allowed to add on top of rules (contact/identity flags stay deterministic).
MODEL_ADDABLE = {
    "RF_CODE_REQUEST", "RF_REMOTE_ACCESS", "RF_DATA_REQUEST", "RF_PAYMENT_REQUEST", "RF_SECRECY",
    "RF_TOO_GOOD", "RF_URGENCY", "RF_THREAT", "RF_EMOTIONAL_PRESSURE", "RF_CHANNEL_SWITCH",
}
# Requests a real organisation never makes; everything else is tolerated from a verified official sender.
NEVER_OFFICIAL = {"RF_CODE_REQUEST", "RF_REMOTE_ACCESS", "RF_DATA_REQUEST", "RF_SECRECY",
                  "RF_SUSPICIOUS_CONTACT", "RF_CHANNEL_SWITCH", "RF_NEW_NUMBER"}
ALERT_THRESHOLD = 25


def _mask(text: str, spans):
    chars = list(text)
    for s, e in spans:
        for i in range(s, e):
            chars[i] = " "
    return "".join(chars)


def _sender_org(sender: dict, channel: str):
    """Org key the sender *verifiably* is (alphanumeric sender id or official e-mail domain), else None."""
    cat = get_catalog()
    dom = C.sender_email_domain(sender)
    if dom:
        c = cat.org_for_domain(dom)
        return compact(c["organisation"]) if c else None
    for field in ("address", "name"):
        v = compact((sender or {}).get(field) or "")
        if v in cat.orgs and channel in ("sms", "email"):
            # alphanumeric SMS sender id equal to the org name
            addr = (sender or {}).get("address") or ""
            if not re.search(r"\d{3}", addr):
                return v
    return None


def _sender_name_claim(sender: dict):
    """Does the display name itself claim to be an org? ("ANAF Rambursări" yes, "Cumpărător PiațaMea" no)."""
    name = norm((sender or {}).get("name") or "").strip()
    if not name:
        return None
    for rx, key in R.GENERIC_CLAIMS:
        m = rx.search(name)
        if m and m.start() == 0:
            return key or "_generic"
    return None


def _empty_result(sid):
    return {"id": sid, "verdict": "SAFE", "scam_type": "NONE", "risk_score": 0, "first_alert": None,
            "red_flags": [], "flags_by_message": [], "evidence": []}


def analyze_core(scenario: dict, model=None) -> dict:
    cat = get_catalog()
    sid = str(scenario.get("id") or "PASTE")
    channel = scenario.get("channel") or "sms"
    sender = scenario.get("sender") or {}
    known = bool(sender.get("known_contact"))
    msgs = [m for m in (scenario.get("messages") or []) if isinstance(m, dict)]
    msgs = sorted(msgs, key=lambda m: m.get("n") or 0)
    if not msgs:
        return _empty_result(sid)

    sender_org = _sender_org(sender, channel)
    name_claim = _sender_name_claim(sender)

    per_msg = []        # list of dict(n, from, flags:set, evidence:list, claims:list, ntext)
    any_suspicious_contact = False
    dom = C.sender_email_domain(sender)
    sender_email_bad = bool(dom) and not cat.is_official_domain(dom)

    prev_sender_ntext = ""
    for i, m in enumerate(msgs):
        n = m.get("n") or (i + 1)
        text = str(m.get("text") or "")
        frm = m.get("from") or "sender"
        rec = {"n": n, "from": frm, "flags": set(), "evidence": [], "claims": [], "text": text}
        if frm != "sender":
            per_msg.append(rec)
            continue
        nt = norm(text)
        found = C.extract(nt)
        for c in found:
            if not c["official"]:
                rec["flags"].add("RF_SUSPICIOUS_CONTACT")
                rec["evidence"].append({"n": n, "flag": "RF_SUSPICIOUS_CONTACT", "span": list(c["span"]), "source": "contact"})
                any_suspicious_contact = True
        masked = _mask(nt, [c["span"] for c in found])
        for flag, span in R.detect(masked, known_contact=known, prev_ntext=prev_sender_ntext):
            rec["flags"].add(flag)
            rec["evidence"].append({"n": n, "flag": flag, "span": list(span), "source": "rule"})
        rec["claims"] = R.org_claims(masked)
        rec["ntext"] = masked
        prev_sender_ntext = masked
        per_msg.append(rec)

    if sender_email_bad:
        first_sender = next((r for r in per_msg if r["from"] == "sender"), None)
        if first_sender is not None:
            first_sender["flags"].add("RF_SUSPICIOUS_CONTACT")
            any_suspicious_contact = True

    # ---- optional model: add high-confidence flags the rules missed
    model_type_probs = None
    if model is not None:
        try:
            flag_probs, model_type_probs = model.predict(scenario)
        except Exception:  # never let the model break the demo
            flag_probs, model_type_probs = None, None
        if flag_probs:
            for rec in per_msg:
                if rec["from"] != "sender":
                    continue
                probs = flag_probs.get(rec["n"], {})
                for flag, p in probs.items():
                    if flag in MODEL_ADDABLE and flag not in rec["flags"] and p >= model.threshold(flag):
                        if _model_vetoed(flag, rec.get("ntext", "")):
                            continue
                        rec["flags"].add(flag)
                        rec["evidence"].append({"n": rec["n"], "flag": flag, "span": None, "source": "model",
                                                "p": round(float(p), 3)})

    # ---- trusted official context: verified sender, only official contacts, no "never official" request
    all_flags = set().union(*[r["flags"] for r in per_msg])
    trusted = sender_org is not None and not (all_flags & NEVER_OFFICIAL)
    if trusted:
        for rec in per_msg:
            rec["flags"] = set()
            rec["evidence"] = []
    # ---- known contact asking for money with no other pressure = normal family/friend talk
    if known and all_flags <= {"RF_PAYMENT_REQUEST", "RF_EMOTIONAL_PRESSURE"}:
        for rec in per_msg:
            rec["flags"].discard("RF_PAYMENT_REQUEST")
            rec["evidence"] = [e for e in rec["evidence"] if e["flag"] != "RF_PAYMENT_REQUEST"]

    # ---- IMPERSONATION: an org claim + (unverified sender or other risk in the thread)
    claim_msgs = [r for r in per_msg if r["claims"]]
    claim_orgs = {k for r in claim_msgs for k, _ in r["claims"]}
    if name_claim:
        claim_orgs.add(name_claim)
    if (claim_msgs or name_claim) and not trusted:
        others = set().union(*[r["flags"] for r in per_msg])
        verified = sender_org is not None and claim_orgs <= {sender_org}
        if not verified or others:
            # attach at the first claim message; for a verified-looking sender wait until risk appears
            if name_claim:
                target = next((r for r in per_msg if r["from"] == "sender"), None)
            else:
                target = claim_msgs[0]
            if verified:
                first_risk = next((r for r in per_msg if r["flags"]), None)
                if first_risk is not None and first_risk["n"] > target["n"]:
                    target = first_risk
            if target is not None:
                target["flags"].add("RF_IMPERSONATION")
                for k, span in target["claims"][:1]:
                    target["evidence"].append({"n": target["n"], "flag": "RF_IMPERSONATION", "span": list(span),
                                               "source": "rule"})

    # ---- cumulative scoring per prefix
    seen, flags_by_message, first_alert = set(), [], None
    for rec in per_msg:
        new = [f for f in FLAG_ORDER if f in rec["flags"] and f not in seen]
        seen |= rec["flags"]
        score = cat.score(seen)
        flags_by_message.append({"n": rec["n"], "flags": [f for f in FLAG_ORDER if f in rec["flags"]],
                                 "new_flags": new, "score_after": score})
        if first_alert is None and score >= ALERT_THRESHOLD:
            first_alert = rec["n"]
    risk = cat.score(seen)
    verdict = cat.verdict(risk)
    red_flags = [f for f in FLAG_ORDER if f in seen]
    full_ntext = " \n ".join(norm(r["text"]) for r in per_msg if r["from"] == "sender")
    full_ntext += " \n " + norm(sender.get("name") or "")
    scam_type = "NONE" if verdict == "SAFE" else choose_type(set(red_flags), full_ntext, claim_orgs, known,
                                                             model_type_probs)
    evidence = [e for r in per_msg for e in r["evidence"]]
    return {
        "id": sid, "verdict": verdict, "scam_type": scam_type, "risk_score": risk,
        "first_alert": first_alert if verdict != "SAFE" else None, "red_flags": red_flags,
        "flags_by_message": flags_by_message, "evidence": evidence,
        "_claim_orgs": sorted(k for k in claim_orgs if k), "_sender_org": sender_org,
    }


_VETO = {
    "RF_CODE_REQUEST": R.NEG_ADVICE,
    "RF_DATA_REQUEST": R.NEG_ADVICE,
}


def _model_vetoed(flag, ntext):
    rx = _VETO.get(flag)
    return bool(rx and ntext and rx.search(ntext))


# ---------------------------------------------------------------- scam type
_TYPE_KW = {
    "TECH_SUPPORT": r"suport(?:ul)?\s+tehnic|microsoft|windows|calculator|laptop|virus|any\s?desk|team\s?viewer|"
                    r"de\s+la\s+distanta|instalati|programul",
    "FAMILY_EMERGENCY": r"\bmami\b|\bmama\b|\btata\b|\btati\b|bunic|nepot|nepoata|\bfiul\b|\bfiica\b|puiule|numar(?:ul)?\s+nou|"
                        r"accident|spital|arestat|cautiune|\bsunt\s+eu\b",
    "MARKETPLACE": r"cumparator|vanzator|anunt|disponibil|livrare\s+sigura|sa\s+primiti\s+banii|primiti\s+banii|"
                   r"piata\s*mea|\bolx\b|produsul|il\s+iau|o\s+iau|curierul\s+va\s+ridica",
    "ACCOUNT_TAKEOVER": r"din\s+greseala|trimis\s+(?:\w+\s+){0,3}cod|cod\s+de\s+\d+\s+cifre|contul\s+(?:meu\s+)?de\s+whatsapp|"
                        r"ti-a\s+venit\s+(?:\w+\s+){0,3}cod",
    "AUTHORITY_IMPERSONATION": r"\banaf\b|fisc|contribuabil|impozit|casa\s+de\s+pensii|pensi|politi|primari|ghiseul|"
                               r"minister|guvern|amenda|dosar|indexare|cnas|tribunal|instanta|comisar|ancheta|procuror|parchet",
    "COURIER_FEE": r"colet|awb|livrar|curier|posta|expeditie|reprogramare|vama|depozit(?:ul)?\s+curier",
    "INVESTMENT": r"investi|crypto|bitcoin|randament|trading|bursa|actiuni|platforma\s+de|profit|broker|portofoliu",
    "ROMANCE": r"iubit|iubito|iubitule|te\s+iubesc|draga\s+mea|dragul\s+meu|ne-am\s+cunoscut|sa\s+ne\s+vedem|"
               r"bilet\s+de\s+avion|dor\s+de\s+tine|inima|militar|misiune",
    "JOB_OFFER": r"\bjob\b|loc\s+de\s+munca|angaj|lucr(?:ati|eaza|ezi)\s+de\s+acasa|like-uri|aprecieri|sarcini|task|"
                 r"recrut|castigati\s+\d+|pe\s+zi\b|comision(?:ul)?\s+pe",
    "PRIZE_LOTTERY": r"castig|tombola|premiu|loteri|extragere|felicitari|ales\s+castigator",
    "BANK_IMPERSONATION": r"banca|bancii|\bcard(?:ul)?\b|cont(?:ul)?\s+bancar|tranzacti|deblocare|plata\s+suspecta|"
                          r"internet\s+banking",
}
_TYPE_KW = {k: re.compile(v) for k, v in _TYPE_KW.items()}
_PRIORITY = ["TECH_SUPPORT", "FAMILY_EMERGENCY", "MARKETPLACE", "ACCOUNT_TAKEOVER", "AUTHORITY_IMPERSONATION",
             "COURIER_FEE", "INVESTMENT", "ROMANCE", "JOB_OFFER", "PRIZE_LOTTERY", "BANK_IMPERSONATION", "OTHER"]


def type_scores(flags: set, ntext: str, claim_orgs: set, known: bool):
    s = {t: 0.0 for t in _PRIORITY}
    for t, rx in _TYPE_KW.items():
        s[t] += min(3, len(rx.findall(ntext)))
    if "RF_REMOTE_ACCESS" in flags:
        s["TECH_SUPPORT"] += 4
    if "RF_NEW_NUMBER" in flags:
        s["FAMILY_EMERGENCY"] += 4
    if "RF_CODE_REQUEST" in flags and "RF_IMPERSONATION" not in flags:
        s["ACCOUNT_TAKEOVER"] += 4
    if "RF_TOO_GOOD" in flags:
        s["PRIZE_LOTTERY"] += 1
        s["INVESTMENT"] += 1
    if claim_orgs & {"anaf", "_police", "_pension", "_gov"}:
        s["AUTHORITY_IMPERSONATION"] += 3
    if "_tech" in claim_orgs:
        s["TECH_SUPPORT"] += 2
    if "_bank" in claim_orgs:
        s["BANK_IMPERSONATION"] += 2
    if "_courier" in claim_orgs:
        s["COURIER_FEE"] += 2
    if "bancadunarea" in claim_orgs:
        s["BANK_IMPERSONATION"] += 3
    if "curierexpres" in claim_orgs:
        s["COURIER_FEE"] += 3
    if "piatamea" in claim_orgs:
        s["MARKETPLACE"] += 2
    if "megashop" in claim_orgs:
        s["PRIZE_LOTTERY"] += 1
    return s


def choose_type(flags, ntext, claim_orgs, known, model_type_probs=None):
    s = type_scores(flags, ntext, claim_orgs, known)
    if model_type_probs:
        for t, p in model_type_probs.items():
            if t in s:
                s[t] += 2.5 * float(p)   # model acts as a soft vote / tiebreaker
    best = max(_PRIORITY, key=lambda t: (s[t], -_PRIORITY.index(t)))
    return best if s[best] > 0 else "OTHER"
