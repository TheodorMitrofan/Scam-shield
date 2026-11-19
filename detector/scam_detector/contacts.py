"""Link / e-mail / phone extraction and the official-contacts check (RF_SUSPICIOUS_CONTACT).

Deterministic and authoritative: the ML model never adds or removes this flag.
"""
import re

from .catalog import get_catalog

_TLDS = (
    "ro|com|net|org|info|eu|io|xyz|top|site|online|app|biz|co|me|ly|link|click|shop|store|"
    "live|life|support|help|club|vip|win|bid|icu|cc|tk|ml|ga|cf|gq|pw|ru|cn|us|uk|de|it|fr|md|"
    "pro|tech|website|space|fun|cloud|page|digital|services|today|world|email|bank|finance|money"
)
_EMAIL = re.compile(r"[a-z0-9._%+\-]+@([a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.(?:" + _TLDS + r"))\b")
_URL = re.compile(
    r"(?<![@\w.\-])(?:https?://)?(?:www\.)?((?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+(?:" + _TLDS + r"))"
    r"(?![a-z0-9\-])(?:[/?#][^\s,;)\"']*)?"
)
_SHORTENER = re.compile(r"\b(?:bit\.ly|tinyurl\.com|t\.me|wa\.me|goo\.gl|cutt\.ly|is\.gd|t\.co)/\S+")
# Romanian-style phone numbers: +40 7xx xxx xxx, 07xx xxx xxx, 0800 100 200, 031 403 91 60 ...
_PHONE = re.compile(r"(?<![\w])(?:\+|00)?(?:40[\s.\-]?)?0?[1-9](?:[\s.\-]?\d){7,9}(?!\d)")


def extract(ntext: str):
    """Return list of dicts {kind, value, span, official} found in normalised text."""
    cat = get_catalog()
    found, taken = [], []

    def overlaps(s, e):
        return any(not (e <= a or s >= b) for a, b in taken)

    for m in _EMAIL.finditer(ntext):
        dom = m.group(1)
        found.append({"kind": "email", "value": m.group(0), "span": (m.start(), m.end()),
                      "official": cat.is_official_domain(dom), "domain": dom})
        taken.append((m.start(), m.end()))
    for m in _SHORTENER.finditer(ntext):
        if overlaps(m.start(), m.end()):
            continue
        found.append({"kind": "url", "value": m.group(0), "span": (m.start(), m.end()),
                      "official": False, "domain": m.group(0).split("/")[0]})
        taken.append((m.start(), m.end()))
    for m in _URL.finditer(ntext):
        if overlaps(m.start(), m.end()):
            continue
        dom = m.group(1)
        found.append({"kind": "url", "value": m.group(0), "span": (m.start(), m.end()),
                      "official": cat.is_official_domain(dom), "domain": dom})
        taken.append((m.start(), m.end()))
    for m in _PHONE.finditer(ntext):
        if overlaps(m.start(), m.end()):
            continue
        val = m.group(0)
        nd = len(re.sub(r"\D", "", val))
        if nd < 9:
            continue
        # skip things that look like amounts/dates/codes rather than phone numbers
        if re.fullmatch(r"\d{6}", val.strip()):
            continue
        found.append({"kind": "phone", "value": val, "span": (m.start(), m.end()),
                      "official": cat.is_official_phone(val)})
        taken.append((m.start(), m.end()))
    return found


def sender_email_domain(sender: dict):
    addr = (sender or {}).get("address") or ""
    m = re.search(r"@([A-Za-z0-9.\-]+)", addr)
    return m.group(1).lower() if m else None
