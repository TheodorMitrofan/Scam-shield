"""Official catalog: red-flag points, verdict bands, scam types, official contacts."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

from .normalize import compact, norm

_PKG_CATALOG = Path(__file__).parent / "data" / "official_catalog.json"
_KIT_CATALOG = Path(__file__).resolve().parents[2] / "Scam_Shield_Public_Kit" / "official_catalog.json"

# Fixed order used everywhere (model heads, CSV output).
FLAG_ORDER = [
    "RF_CODE_REQUEST", "RF_REMOTE_ACCESS", "RF_DATA_REQUEST", "RF_PAYMENT_REQUEST",
    "RF_SUSPICIOUS_CONTACT", "RF_NEW_NUMBER", "RF_SECRECY", "RF_TOO_GOOD",
    "RF_IMPERSONATION", "RF_URGENCY", "RF_THREAT", "RF_EMOTIONAL_PRESSURE", "RF_CHANNEL_SWITCH",
]


def digits(s: str) -> str:
    d = re.sub(r"\D", "", s or "")
    if d.startswith("0040"):
        d = d[4:]
    elif d.startswith("40") and len(d) >= 11:
        d = d[2:]
    return d.lstrip("0")


class Catalog:
    def __init__(self, data: dict):
        self.points: dict = data["red_flag_points"]
        self.bands: dict = data["verdict_bands"]
        self.scam_types: list = data["scam_types"]
        self.contacts: list = data["official_contacts"]
        self.official_domains = {c["website"].lower() for c in self.contacts if c.get("website")}
        self.official_phones = {digits(c["phone"]) for c in self.contacts if c.get("phone")}
        # org key ("bancadunarea") -> contact record
        self.orgs = {compact(c["organisation"]): c for c in self.contacts}

    def score(self, flags) -> int:
        return min(100, sum(self.points.get(f, 0) for f in set(flags)))

    def verdict(self, score: int) -> str:
        for name, (lo, hi) in self.bands.items():
            if lo <= score <= hi:
                return name
        return "SCAM" if score > 100 else "SAFE"

    def is_official_domain(self, domain: str) -> bool:
        d = norm(domain).lower().strip(".")
        if d.startswith("www."):
            d = d[4:]
        return any(d == o or d.endswith("." + o) for o in self.official_domains)

    def is_official_phone(self, phone: str) -> bool:
        return digits(phone) in self.official_phones

    def org_for_domain(self, domain: str):
        d = norm(domain).lower()
        for c in self.contacts:
            w = (c.get("website") or "").lower()
            if w and (d == w or d.endswith("." + w)):
                return c
        return None


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    path = os.environ.get("SCAM_CATALOG")
    for p in [path, _KIT_CATALOG, _PKG_CATALOG]:
        if p and Path(p).is_file():
            with open(p, encoding="utf-8") as f:
                return Catalog(json.load(f))
    raise FileNotFoundError("official_catalog.json not found")
