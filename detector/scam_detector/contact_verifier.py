from __future__ import annotations

import re
from typing import Dict, Optional
from .catalog import Catalog
from .text_utils import extract_urls_and_domains, extract_emails, normalize_text, PHONE_REGEX

_GENERIC_FINANCIAL_OR_AUTH_RX = re.compile(
    r"\b(?:banca(?:\s+dvs\.?|\s+dumneavoastra)?|departamentul\s+(?:de\s+)?securitate|antifrauda|politia)\b"
)


class ContactVerifier:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def check_suspicious_contact(
        self,
        message_text: str,
        sender_info: Optional[Dict] = None
    ) -> bool:
        """
        Returns True if a link, sender address, or claimed phone number is NOT on the official list.
        """
        if not message_text:
            return False

        # 1. Check URLs in message text (supports defanged links & HTTP user@host traps)
        urls = extract_urls_and_domains(message_text)
        for _, domain in urls:
            if not self.catalog.is_official_website(domain):
                return True

        # 2. Check emails in message text
        emails = extract_emails(message_text)
        for email in emails:
            domain = email.split("@")[-1]
            if not self.catalog.is_official_website(domain):
                return True

        # 3. Check sender info and embedded phone numbers when claiming official/financial organisations
        address = (sender_info.get("address") or "") if isinstance(sender_info, dict) else ""
        name = (sender_info.get("name") or "") if isinstance(sender_info, dict) else ""
        norm_name = normalize_text(name)
        norm_addr = normalize_text(address)
        norm_msg = normalize_text(message_text)

        has_call_prompt = bool(re.search(r"\b(?:sunati|suna|apelati|contactati|informatii)\b", norm_msg))
        body_phones = PHONE_REGEX.findall(message_text) if has_call_prompt else []

        for org in self.catalog.official_contacts:
            org_name = normalize_text(org.get("organisation", ""))
            if not org_name:
                continue
            org_compact = org_name.replace(" ", "")
            org_rx = re.compile(rf"\b{re.escape(org_name)}\b|\b{re.escape(org_compact)}\b")

            claims_org_sender = bool(org_rx.search(norm_name) or org_rx.search(norm_addr))
            claims_org_body = bool(org_rx.search(norm_msg))

            if claims_org_sender:
                if "@" in address:
                    email_domain = address.split("@")[-1].lower().strip()
                    if not self.catalog.is_official_website(email_domain):
                        return True
                if org.get("phone") and any(ch.isdigit() for ch in address):
                    if not self.catalog.is_official_phone(address):
                        return True

            if (claims_org_body or claims_org_sender) and body_phones:
                for bp in body_phones:
                    clean_bp = "".join(ch for ch in bp if ch.isdigit())
                    if len(clean_bp) >= 9 and not self.catalog.is_official_phone(bp):
                        return True

        # Also catch generic bank/authority phone spoofing ("Banca dvs: sunati la 0744 123 456")
        if has_call_prompt and body_phones and _GENERIC_FINANCIAL_OR_AUTH_RX.search(norm_msg):
            for bp in body_phones:
                clean_bp = "".join(ch for ch in bp if ch.isdigit())
                if len(clean_bp) >= 9 and not self.catalog.is_official_phone(bp):
                    return True

        return False
