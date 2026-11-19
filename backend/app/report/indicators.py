"""Extracts the scammer's identifiers from a conversation (evidence for the report) and defangs them,
so a link or address can never be clicked from the report (brief: never offer the message's links)."""

import re

from app.schemas import Scenario
from app.schemas.report import Indicator

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE)
_URL = re.compile(
    r"(?:(?:https?|hxxps?)://)?(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,24}(?:/[^\s,;)\"'<>]*)?",
    re.IGNORECASE,
)
# Romanian numbers, including the masked ones used in the kit ("+40 7xx xxx 318", "0800 100 200").
_PHONE = re.compile(r"(?<![\w+])(?:\+40|0040|0)[\s.-]?[0-9x]{3}[\s.-]?[0-9x]{3}[\s.-]?[0-9x]{3}(?![\w])", re.IGNORECASE)
_IBAN = re.compile(r"\bRO\d{2}\s?[A-Z]{4}(?:\s?[0-9A-Z]{4}){4}\b")
_AMOUNT = re.compile(r"\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?\s?(?:lei|ron|€|eur(?:o)?|\$|usd)\b|\d+(?:,\d{1,2})?\s?€", re.IGNORECASE)

# Words that look like domains but are not ("dvs.Card" never happens with a space, but abbreviations can).
_NOT_DOMAINS = {"dvs.", "dl.", "dna."}


def defang(value: str) -> str:
    """bancadunarea-securitate.com → bancadunarea-securitate[.]com ; https:// → hxxps:// ; @ → [@]"""
    v = re.sub(r"^http", "hxxp", value, flags=re.IGNORECASE)
    if "@" in v:
        local, _, domain = v.partition("@")
        return f"{local}[@]{domain.replace('.', '[.]')}"
    scheme, sep, rest = v.rpartition("://")
    host, slash, path = rest.partition("/")
    return f"{scheme}{sep}{host.replace('.', '[.]')}{slash}{path}"


def defang_text(text: str) -> str:
    """Defangs every e-mail address and link inside free text (message bodies, sender fields)."""
    if not text:
        return text
    out, last = [], 0
    spans = sorted(
        [(m.start(), m.end(), m.group(0)) for m in _EMAIL.finditer(text)]
        + [(m.start(), m.end(), m.group(0)) for m in _URL.finditer(text)],
        key=lambda x: (x[0], -x[1]),
    )
    for a, b, value in spans:
        if a < last:
            continue  # url inside an already-defanged e-mail
        core = value.rstrip(".")
        if core.lower() in _NOT_DOMAINS or core.replace(".", "").isdigit():
            continue
        out.append(text[last:a])
        out.append(defang(core) + value[len(core):])
        last = b
    out.append(text[last:])
    return "".join(out)


def _add(out: list[Indicator], seen: set, kind: str, value: str, n: int | None) -> None:
    key = (kind, value.lower())
    if key in seen:
        return
    seen.add(key)
    display = defang(value) if kind in ("url", "email") else value
    out.append(Indicator(kind=kind, value=value, display=display, message_n=n))


def extract_indicators(scenario: Scenario) -> list[Indicator]:
    out: list[Indicator] = []
    seen: set = set()

    # The sender field itself (e-mail address / phone / username) is evidence too.
    addr = (scenario.sender.address or "").strip()
    if addr:
        if _EMAIL.fullmatch(addr):
            _add(out, seen, "email", addr, None)
        elif _PHONE.fullmatch(addr):
            _add(out, seen, "phone", addr, None)

    for m in scenario.messages:
        if m.from_.value != "sender":
            continue  # only what the suspect wrote
        text = m.text or ""
        taken: list[tuple[int, int]] = []
        for rx, kind in ((_EMAIL, "email"), (_IBAN, "iban"), (_URL, "url"), (_PHONE, "phone"), (_AMOUNT, "amount")):
            for match in rx.finditer(text):
                a, b = match.span()
                if any(a < tb and b > ta for ta, tb in taken):
                    continue  # already part of an e-mail/url
                value = match.group(0).rstrip(".")
                if kind == "url" and (value.lower() in _NOT_DOMAINS or value.replace(".", "").isdigit()):
                    continue
                taken.append((a, b))
                _add(out, seen, kind, value, m.n)
    return out
