from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

FLAG_ORDER = [
    "RF_CODE_REQUEST", "RF_REMOTE_ACCESS", "RF_DATA_REQUEST", "RF_PAYMENT_REQUEST",
    "RF_SUSPICIOUS_CONTACT", "RF_NEW_NUMBER", "RF_SECRECY", "RF_TOO_GOOD",
    "RF_IMPERSONATION", "RF_URGENCY", "RF_THREAT", "RF_EMOTIONAL_PRESSURE", "RF_CHANNEL_SWITCH",
]


class Catalog:
    def __init__(self, catalog_path: Optional[str] = None):
        if catalog_path is None:
            pkg_dir = Path(__file__).resolve().parent
            repo_root = pkg_dir.parents[1]
            candidates = [
                pkg_dir / "data" / "official_catalog.json",
                repo_root / "Scam_Shield_Public_Kit" / "official_catalog.json",
                Path("Scam_Shield_Public_Kit/official_catalog.json"),
                Path("official_catalog.json"),
            ]
            for c in candidates:
                if c.is_file():
                    catalog_path = str(c)
                    break

        if catalog_path and os.path.exists(catalog_path):
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {
                "red_flag_points": {
                    "RF_CODE_REQUEST": 35, "RF_REMOTE_ACCESS": 35, "RF_DATA_REQUEST": 30,
                    "RF_PAYMENT_REQUEST": 25, "RF_SUSPICIOUS_CONTACT": 25, "RF_NEW_NUMBER": 20,
                    "RF_SECRECY": 20, "RF_TOO_GOOD": 20, "RF_IMPERSONATION": 15,
                    "RF_URGENCY": 15, "RF_THREAT": 15, "RF_EMOTIONAL_PRESSURE": 10, "RF_CHANNEL_SWITCH": 10,
                },
                "verdict_bands": {"SAFE": [0, 24], "SUSPICIOUS": [25, 49], "SCAM": [50, 100]},
                "scam_types": [
                    "BANK_IMPERSONATION", "COURIER_FEE", "AUTHORITY_IMPERSONATION", "FAMILY_EMERGENCY",
                    "TECH_SUPPORT", "MARKETPLACE", "ACCOUNT_TAKEOVER", "INVESTMENT",
                    "ROMANCE", "JOB_OFFER", "PRIZE_LOTTERY", "OTHER", "NONE",
                ],
                "official_contacts": [
                    {"organisation": "Banca Dunărea", "website": "bancadunarea.ro", "phone": "0800 100 200"},
                    {"organisation": "CurierExpres", "website": "curierexpres.ro", "phone": "0800 300 400"},
                    {"organisation": "PiațaMea", "website": "piatamea.ro", "phone": None},
                    {"organisation": "MegaShop", "website": "megashop.ro", "phone": "0800 500 600"},
                    {"organisation": "ANAF", "website": "anaf.ro", "phone": "031 403 91 60"},
                ],
            }

        self.red_flag_points: Dict[str, int] = data["red_flag_points"]
        self.verdict_bands: Dict[str, List[int]] = data["verdict_bands"]
        self.scam_types: List[str] = data["scam_types"]
        self.official_contacts: List[Dict[str, Optional[str]]] = data["official_contacts"]
        # Compatibility aliases for model_detector / cli / evaluate
        self.points = self.red_flag_points
        self.bands = self.verdict_bands

    def get_verdict(self, score: int) -> str:
        score = max(0, min(100, score))
        for verdict, (low, high) in self.verdict_bands.items():
            if low <= score <= high:
                return verdict
        return "SCAM" if score >= 50 else ("SUSPICIOUS" if score >= 25 else "SAFE")

    def is_official_website(self, domain: str) -> bool:
        domain = domain.lower().strip()
        for c in self.official_contacts:
            official_site = c.get("website")
            if official_site:
                official_site = official_site.lower().strip()
                if domain == official_site or domain.endswith("." + official_site):
                    return True
        return False

    def is_official_phone(self, phone: str) -> bool:
        cleaned_phone = "".join(ch for ch in phone if ch.isdigit())
        for c in self.official_contacts:
            official_phone = c.get("phone")
            if official_phone:
                cleaned_official = "".join(ch for ch in official_phone if ch.isdigit())
                if cleaned_phone and (cleaned_phone == cleaned_official or cleaned_phone.endswith(cleaned_official)):
                    return True
        return False


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    return Catalog(os.environ.get("SCAM_CATALOG"))
