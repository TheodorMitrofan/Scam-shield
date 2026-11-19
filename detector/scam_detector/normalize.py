"""Text normalisation that keeps character offsets stable.

`norm(text)` returns a lowercase, diacritic-free string of EXACTLY the same length
as the input, so regex match spans on the normalised text are valid spans in the
original text (used for evidence highlighting).
"""
import re
import unicodedata

_EXTRA = {
    "ș": "s", "ş": "s", "ț": "t", "ţ": "t", "Ș": "s", "Ş": "s", "Ț": "t", "Ţ": "t",
    "’": "'", "‘": "'", "`": "'", "´": "'", "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "‑": "-", " ": " ",
}


def _fold_char(ch: str) -> str:
    if ch in _EXTRA:
        return _EXTRA[ch]
    low = ch.lower()
    if len(low) != 1:
        low = ch
    decomposed = unicodedata.normalize("NFKD", low)
    base = "".join(c for c in decomposed if not unicodedata.combining(c))
    if len(base) == 1:
        return base
    return low if len(low) == 1 else " "


def norm(text: str) -> str:
    if not text:
        return ""
    return "".join(_fold_char(c) for c in text)


def compact(text: str) -> str:
    """Normalised text with everything except letters/digits removed ("Banca Dunărea" -> "bancadunarea")."""
    return re.sub(r"[^a-z0-9]", "", norm(text or ""))


_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


def sentences(text: str):
    """Yield (start, end) spans of sentences in `text` (works on normalised text too)."""
    pos = 0
    for m in _SENT_SPLIT.finditer(text):
        if m.start() > pos:
            yield pos, m.start()
        pos = m.end()
    if pos < len(text):
        yield pos, len(text)
