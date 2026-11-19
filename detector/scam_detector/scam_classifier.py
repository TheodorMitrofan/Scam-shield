import os
import re
import joblib
from typing import Dict, Optional, Set
from .text_utils import deobfuscate_for_detection


class ScamClassifier:
    def __init__(self):
        self.model = None
        self._type_pipeline = None
        model_path = os.path.join(os.path.dirname(__file__), "trained_model.joblib")
        if os.path.exists(model_path):
            try:
                loaded = joblib.load(model_path)
                self.model = loaded
                if isinstance(loaded, dict) and loaded.get("version", 1) >= 2:
                    self._type_pipeline = loaded.get("type_pipeline")
                else:
                    self._type_pipeline = loaded
            except Exception as e:
                print(f"Warning: Could not load trained_model.joblib: {e}")

    def get_model_bundle(self) -> Optional[Dict]:
        return self.model if isinstance(self.model, dict) else None

    def classify(
        self,
        red_flags: Set[str],
        full_text: str,
        sender_info: Optional[Dict] = None
    ) -> str:
        if not red_flags:
            return "NONE"

        text_norm = deobfuscate_for_detection(full_text)
        sender_name = deobfuscate_for_detection((sender_info.get("name") or "") if isinstance(sender_info, dict) else "")
        sender_addr = deobfuscate_for_detection((sender_info.get("address") or "") if isinstance(sender_info, dict) else "")
        known_contact = bool(sender_info.get("known_contact", False)) if isinstance(sender_info, dict) else False
        combined_text = f"{sender_name} {sender_addr} {text_norm}".strip()

        # 1.1 TECH_SUPPORT
        if "RF_REMOTE_ACCESS" in red_flags or any(t in combined_text for t in [
            "anydesk", "teamviewer", "suport tehnic", "suportul tehnic", "partajare a ecranului", "partajare ecran", "desktopul",
        ]):
            if "RF_REMOTE_ACCESS" in red_flags or "suport tehnic" in combined_text or "suportul tehnic" in combined_text or "virusi" in combined_text:
                return "TECH_SUPPORT"

        # 1.2 ACCOUNT_TAKEOVER
        if "RF_CODE_REQUEST" in red_flags:
            if any(p in combined_text for p in [
                "din greseala", "ti-am trimis din greseala", "mi-l poti trimite inapoi",
                "trimis un cod", "cod de 6 cifre", "sase cifre", "inapoi", "recupera contul", "recuperare",
            ]) and "casa de pensii" not in combined_text:
                return "ACCOUNT_TAKEOVER"
        if known_contact and ("RF_CODE_REQUEST" in red_flags or "RF_DATA_REQUEST" in red_flags) and not re.search(r"\b(?:banca|anaf|curier|pensii)\b", combined_text):
            return "ACCOUNT_TAKEOVER"

        # 1.3 MARKETPLACE (must precede COURIER_FEE because OLX/PiataMea scams mention sending a courier)
        if any(m in combined_text for m in ["piatamea", "piata mea", "olx", "cumparator", "bicicleta", "livrare sigura"]) or re.search(r"\banunt(?:ul)?\b", combined_text):
            return "MARKETPLACE"

        # 1.4 ROMANCE (must precede COURIER_FEE & BANK_IMPERSONATION for customs/gift-card romance stories)
        is_romance_frame = any(r in combined_text for r in [
            "dragostea mea", "draga mea", "dragul meu", "iubirea mea", "iubito", "iubitule",
            "te iubesc", "militar", "misiune militara", "baza militara", "baza indepartata",
            "platforma petroliera", "capitan", "sufletul meu", "suflet drag", "sufletul meu pereche",
            "ne casatorim", "hello dear", "paysafe", "card preplatit",
        ])
        if is_romance_frame:
            return "ROMANCE"

        # 1.5 FAMILY_EMERGENCY
        has_family_word = bool(re.search(
            r"\b(?:mami|mama|mamico|tati|taticule|tata|buni|bunico|bunica|bunicul|bunicului|copilul|copilului|"
            r"nepot|nepotul|nepotului|nepoata|fiul|fiica|mamei|tatalui)\b",
            combined_text,
        ))
        if ("RF_NEW_NUMBER" in red_flags or "RF_SECRECY" in red_flags or has_family_word) and (
            has_family_word or "RF_NEW_NUMBER" in red_flags
        ):
            if any(w in combined_text for w in [
                "numar nou", "noul numar", "telefon", "cartela", "mami", "tati", "taticule", "buni",
                "factura", "accident", "spital", "bani", "transfer", "revolut", "avocat",
                "inchisoare", "cautiune", "victimei", "retinut", "ajuta",
            ]):
                return "FAMILY_EMERGENCY"

        # 1.6 INVESTMENT (must precede BANK_IMPERSONATION for withdrawal/unlock fees; use word boundaries)
        if any(i in combined_text for i in ["crypto", "criptomonede", "bitcoin", "invest", "randament", "trading"]) or re.search(
            r"\b(?:actiuni|bursa)\b|\bprofit\b[^.!?]{0,25}\b(?:garantat|retrag|lun|saptaman)", combined_text
        ):
            return "INVESTMENT"

        # 1.7 JOB_OFFER
        if any(j in combined_text for j in [
            "oferta de munca", "recrutare", "like-uri", "like la", "marketing", "youtube",
            "sarcini", "sarcinile", "lucru de acasa", "angajam", "evaluari", "google maps", "colaboratori",
        ]) or re.search(r"\bjob\b", combined_text):
            return "JOB_OFFER"

        # 1.8 Health / medical miracle scam -> OTHER (must precede AUTHORITY_IMPERSONATION / COURIER_FEE)
        is_health_product = any(h in combined_text for h in ["tratament", "pastile", "medicament", "sanatate vasculara", "nanotehnologic", "vasele", "colesterol", "articulatii"])
        if is_health_product:
            return "OTHER"

        # 1.9 AUTHORITY_IMPERSONATION (precedes BANK_IMPERSONATION even when thieves/bank account mentioned)
        if any(a in combined_text for a in [
            "anaf", "casa de pensii", "casa nationala de pensii", "politia", "politie", "comisar", "procuror",
            "diicot", "executor judecatoresc", "executant judecatoresc", "poprire", "sechestru",
            "minister", "guvern", "pensia dumneavoastra", "pensia va creste", "ghiseul", "executarea silita", "executare silita",
        ]) or re.search(r"\bamenda\b", combined_text):
            return "AUTHORITY_IMPERSONATION"

        # 1.10 PRIZE_LOTTERY (must precede COURIER_FEE when prize asks a shipping fee)
        if "RF_TOO_GOOD" in red_flags and any(p in combined_text for p in [
            "tombola", "premiu", "castigat", "castigatorul", "telefon nou", "megashop", "sondaj", "voucher", "loteria",
        ]):
            return "PRIZE_LOTTERY"

        # 1.11 COURIER_FEE (Romanian & English courier patterns)
        has_courier_word = any(c in combined_text for c in [
            "curier", "curierexpres", "colet", "awb", "livrare", "reprogramare",
            "package", "parcel", "delivery", "customs", "shipping",
        ]) or bool(re.search(r"\b(?:dhl|fedex|dpd|sameday|fancourier|cargus|vama)\b", combined_text))
        if has_courier_word:
            if "RF_PAYMENT_REQUEST" in red_flags or "RF_DATA_REQUEST" in red_flags or "taxa" in combined_text or "fee" in combined_text:
                return "COURIER_FEE"

        # 1.11 BANK_IMPERSONATION
        if any(b in combined_text for b in [
            "bancadunarea", "banca dunarea", "banca transilvania", "raiffeisen", "revolut",
            "unicredit", "cont de siguranta", "contul de siguranta", "cardul dvs", "departamentul de securitate", "antifrauda",
        ]) or re.search(r"\b(?:banca|bancii|bcr|brd|ing)\b", combined_text) or (
            re.search(r"\bcard\b", combined_text) and ("RF_THREAT" in red_flags or "RF_IMPERSONATION" in red_flags)
        ):
            return "BANK_IMPERSONATION"

        # 2. Calibrated Trained ML Ensemble Inference (probabilistic decision)
        if self._type_pipeline is not None:
            try:
                probs = self._type_pipeline.predict_proba([combined_text])[0]
                classes = self._type_pipeline.classes_
                best_idx = int(probs.argmax())
                best_type = str(classes[best_idx])
                best_prob = float(probs[best_idx])
                if best_type != "NONE" and best_prob >= 0.42:
                    return best_type
            except Exception:
                pass

        return "OTHER"
