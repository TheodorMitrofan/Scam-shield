import re
from typing import List, Tuple
from urllib.parse import urlparse

DIACRITICS_MAP = {
    'ă': 'a', 'Ă': 'A',
    'â': 'a', 'Â': 'A',
    'î': 'i', 'Î': 'I',
    'ș': 's', 'Ș': 'S',
    'ş': 's', 'Ş': 'S',
    'ț': 't', 'Ț': 'T',
    'ţ': 't', 'Ţ': 'T',
}

HOMOGLYPH_MAP = {
    **DIACRITICS_MAP,
    'а': 'a', 'А': 'A', 'е': 'e', 'Е': 'E', 'о': 'o', 'О': 'O',
    'р': 'p', 'Р': 'P', 'с': 'c', 'С': 'C', 'х': 'x', 'Х': 'X',
    'і': 'i', 'І': 'I', 'у': 'y', 'У': 'Y', 'к': 'k', 'К': 'K',
    'м': 'm', 'М': 'M', 'т': 't', 'Т': 'T', 'в': 'b', 'В': 'B',
    'н': 'h', 'Н': 'H',
    'α': 'a', 'ο': 'o', 'ε': 'e', 'ρ': 'p',
}

_LEET_MAP = str.maketrans({'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '@': 'a', '$': 's'})
# Matches spaced-out single-character runs of length >= 4 (e.g. "A n y D e s k" -> "AnyDesk")
_SPACED_WORD_RX = re.compile(r'(?<![a-z0-9])(?:[a-z]\s){3,}[a-z](?![a-z0-9])', re.IGNORECASE)


def remove_diacritics(text: str) -> str:
    """Replaces Romanian diacritics and common homoglyphs with plain Latin characters."""
    if not text:
        return ""
    return "".join(HOMOGLYPH_MAP.get(ch, ch) for ch in text)


def normalize_preserve_length(text: str) -> str:
    """
    Lowercases and maps diacritics/homoglyphs 1-to-1 while preserving exact string length
    so regex [start, end) character spans align cleanly with the original text.
    """
    if not text:
        return ""
    out = []
    for ch in text:
        mapped = HOMOGLYPH_MAP.get(ch, ch)
        low = mapped.lower()
        out.append(low if len(low) == 1 else mapped)
    return "".join(out)


def normalize_text(text: str) -> str:
    """Lowercases, strips diacritics/homoglyphs, and collapses extra whitespace."""
    if not text:
        return ""
    plain = remove_diacritics(text.lower())
    cleaned = re.sub(r'\s+', ' ', plain)
    return cleaned.strip()


# --------------------------------------------------------------------------------------------- typo tolerance
# Distinctive keywords the rules look for. A token one typo away (Damerau-Levenshtein: a letter changed, missing,
# doubled or two letters swapped; two typos for words of 10+ letters) is rewritten to the keyword before the rules
# run, so "tobmola", "catigatorul", "suporrtul", "virrusi" or "AnyDek" still match.
# Deliberately NOT listed: keywords with an ordinary Romanian word one typo away, which would cause false alarms on
# genuine messages, e.g. platiti/platit ("am platit deja"), achitati/achitat, politia/politica, cardului/cadrului,
# expira/expirat, transfer/transferat, instalati/instalat.
_TYPO_LEXICON = frozenset({
    # prizes / too good to be true
    "castigatorul", "castigat", "castigati", "tombola", "premiu", "premiul", "felicitari", "voucher", "garantat",
    # impersonation
    "suport", "suportul", "tehnic", "bancadunarea", "dunarea", "curierexpres", "megashop", "microsoft",
    "windows", "defender", "procuror", "procurorul", "ghiseul", "reprogramare",
    # threats
    "virusi", "infectat", "blocat", "deblocare", "suspendat",
    # remote access
    "anydesk", "teamviewer", "rustdesk", "distanta",
    # urgency
    "urgent", "urgenta", "imediat", "grabiti",
})
_TYPO_MIN_LEN = 6
_TYPO_CORE_RX = re.compile(r"^([^a-z]*)([a-z]+)([^a-z]*)$")


def _damerau_levenshtein(a: str, b: str, limit: int) -> int:
    """Optimal string alignment distance, stopping early once it exceeds `limit`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if prev2 is not None and i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[-1]


def _correct_word(word: str) -> str:
    if len(word) < _TYPO_MIN_LEN or word in _TYPO_LEXICON:
        return word
    best, best_key = word, None
    for kw in _TYPO_LEXICON:
        if kw[0] != word[0]:  # typos rarely hit the first letter; this also keeps false matches down
            continue
        limit = 2 if len(kw) >= 10 else 1
        d = _damerau_levenshtein(word, kw, limit)
        if d <= limit:
            key = (d, abs(len(kw) - len(word)), kw)
            if best_key is None or key < best_key:
                best, best_key = kw, key
    return best


def correct_typos(norm_text: str) -> str:
    """Rewrites near-miss keywords in already-normalized text. Tokens with digits, '.', '@', '/', '-' (links,
    e-mails, amounts, codes, compound forms like "mi-am") are never touched."""
    out = []
    for tok in norm_text.split(" "):
        m = _TYPO_CORE_RX.match(tok)
        out.append(f"{m.group(1)}{_correct_word(m.group(2))}{m.group(3)}" if m else tok)
    return " ".join(out)


def deobfuscate_for_detection(text: str) -> str:
    """
    Normalizes text AND removes common adversarial obfuscation:
    - Spaced single letters ("A n y D e s k" -> "anydesk")
    - Leet-speak inside mixed letter tokens ("c0dul", "bl0cat", "b@nca") while leaving pure numbers intact.
    - Single typos in distinctive keywords ("tobmola" -> "tombola"), see `correct_typos`.
    """
    norm = normalize_text(text)
    if not norm:
        return ""

    # 1. Rejoin spaced single-letter sequences of >= 4 chars
    norm = _SPACED_WORD_RX.sub(lambda m: m.group(0).replace(" ", ""), norm)

    # 2. Decode leet substitutions inside tokens that already contain Latin letters
    tokens = norm.split(" ")
    decoded = []
    for tok in tokens:
        tok_core = tok.strip(".,;:!?()[]{}\"'")
        if any('a' <= ch <= 'z' for ch in tok_core) and any(ch in '013457@$' for ch in tok_core):
            if not re.fullmatch(r'[\d.,]+(?:h|lei|ron|eur|euro)?', tok_core):
                tok = tok.translate(_LEET_MAP)
        decoded.append(tok)
    return correct_typos(" ".join(decoded))


URL_REGEX = re.compile(
    r'(?:https?://)?(?:[a-zA-Z0-9_.!~*\'()%=+$,;&-]+@)?(?:[a-zA-Z0-9\u0400-\u04FF-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?',
    re.IGNORECASE,
)

EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE,
)

PHONE_REGEX = re.compile(
    r'(?:\+?40\s?|0)[23789][0-9\s.x-]{7,12}',
    re.IGNORECASE,
)


def extract_urls_and_domains(text: str) -> List[Tuple[str, str]]:
    """
    Extracts all URLs and returns a list of (raw_url, domain).
    Supports defanged URLs ('domain[.]com', 'hxxp://...') and preserves non-ASCII homoglyphs
    so spoofed domains fail official whitelist checks.
    """
    if not text:
        return []

    cleaned_text = text.replace("[.]", ".").replace("hxxp", "http")
    matches = URL_REGEX.findall(cleaned_text)
    results = []
    for raw in matches:
        raw_clean = raw.rstrip('.,;!?:)')
        parse_target = raw_clean if "://" in raw_clean else f"http://{raw_clean}"
        try:
            parsed = urlparse(parse_target)
            domain = parsed.hostname or parsed.netloc or parsed.path.split('/')[0]
            domain = domain.split(':')[0].strip().lower()
            if "." in domain:
                results.append((raw_clean, domain))
        except Exception:
            pass
    return results


def extract_emails(text: str) -> List[str]:
    if not text:
        return []
    return [e.lower() for e in EMAIL_REGEX.findall(text)]
