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


def deobfuscate_for_detection(text: str) -> str:
    """
    Normalizes text AND removes common adversarial obfuscation:
    - Spaced single letters ("A n y D e s k" -> "anydesk")
    - Leet-speak inside mixed letter tokens ("c0dul", "bl0cat", "b@nca") while leaving pure numbers intact.
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
    return " ".join(decoded)


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
