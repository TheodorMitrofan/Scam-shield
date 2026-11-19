import re
from typing import Dict, List, Optional, Tuple
from .catalog import Catalog
from .text_utils import deobfuscate_for_detection, normalize_preserve_length
from .contact_verifier import ContactVerifier
from .semantic_nli import SemanticNLIEnsemble

_WORD_BOUNDARY_ORG_RX = re.compile(
    r"\bbanca(?=:|\s+(?:dvs|dumneavoastra)\b)|\b(?:banc(?:a|ii)\s+dunarea|bancadunarea|curier\s*expres|anaf|megashop|mega\s*shop|"
    r"suport(?:ul)?\s+tehnic|departament(?:ul)?\s+(?:de\s+)?(?:antifraud[ae]|fraud[ae]|securitate)|"
    r"siguranta\s+financiara\s+a\s+bancii|casa\s+(?:nationala\s+)?de\s+pensii|posta\s+romana|"
    r"banc(?:a|ii)\s+transilvania|bcr|brd|ing|raiffeisen|revolut|unicredit|"
    r"microsoft|windows\s+defender|digi|politia\s+romana|politia|comisar(?:ul)?|"
    r"procuror(?:ul)?|diicot|execut(?:or|ant)(?:ul)?\s+judecatoresc|minister(?:ul)?\s+\w+|"
    r"enel(?:\s+energie)?|electrica|apa\s+nova|tehnician(?:ul)?|"
    r"dhl|fedex|fancourier|sameday|dpd|cargus|ghiseul(?:\.ro)?)\b"
)

_SAFETY_ADVICE_RX = re.compile(
    r"\b(?:nu\s+(?:va|ne)\s+(?:vom|va|cerem|solicitam|solicita)\s+(?:niciodata\s+)?(?:cere|solicita|cer)|"
    r"banca\s+nu\s+(?:solicita|va\s+cere)\s+niciodata|"
    r"ai\s+grija\s+sa\s+nu\b|"
    r"sa\s+nu\s+(?:instalezi|instalati|descarci|descarcati|dai|dati|trimiti|trimiteti|comunici|comunicati)\b|"
    r"nu\s+(?:il\s+|o\s+)?(?:comunicati|comunica|trimiteti|trimite|dati|da|spuneti|spune|introduceti|divulgati)\b[^.!?]{0,45}\b(?:nimanui|niciodata|altor\s+persoane|cod|datele)|"
    r"nu\s+am\s+nevoie\s+de\s+bani|"
    r"mergeti\s+la\s+(?:orice\s+)?sucursala|prezentati-va\s+la\s+ghiseu|la\s+ghiseul\s+bancii)\b"
)


class RedFlagDetector:
    def __init__(self, catalog: Catalog, model_bundle: Optional[Dict] = None):
        self.catalog = catalog
        self.contact_verifier = ContactVerifier(catalog)
        self.semantic_nli = SemanticNLIEnsemble(model_bundle=model_bundle)

    def detect_flags_for_message(
        self,
        message_text: str,
        sender_info: Optional[Dict] = None,
        context_history: Optional[List[Dict]] = None,
        is_from_reader: bool = False
    ) -> List[str]:
        """
        Analyzes a single message within the context of preceding messages.
        Returns an ordered list of newly detected red flags in order of textual appearance.
        If the message is from the 'reader' (victim), it does NOT generate scam red flags.
        """
        if is_from_reader or not message_text:
            return []

        text_norm = deobfuscate_for_detection(message_text)
        flags: List[str] = []

        sender_name = deobfuscate_for_detection((sender_info.get("name") or "") if isinstance(sender_info, dict) else "")
        known_contact = sender_info.get("known_contact", False) if isinstance(sender_info, dict) else False

        def add_flag(flag_name: str):
            if flag_name not in flags:
                flags.append(flag_name)

        is_safety_or_branch_notice = bool(_SAFETY_ADVICE_RX.search(text_norm))

        # -------------------------------------------------------------
        # 1. RF_NEW_NUMBER (20 pts)
        # -------------------------------------------------------------
        has_family_mention = bool(re.search(
            r"\b(?:mami|mama|mamico|tati|taticule|tata|buni|bunico|bunicule|copilul\s+tau|nepot(?:ul)?|nepoata|fiul|fiica|unchi|matusa)\b",
            text_norm,
        ))
        new_num_tokens = [
            "numarul nou", "numar nou", "noul numar", "noul meu numar",
            "mi s-a stricat telefonul", "mi s-a stricat tel", "mi-am pierdut telefonul",
            "mi-am schimbat numarul", "mi am schimbat numarul", "schimbat numarul",
            "schimbat nr", "salveaza-l", "salveaza l", "acesta e noul meu numar",
            "asta e numarul nou", "numarul meu nou", "cartela unui coleg",
            "mi s-a inchis telefonul", "telefonul vechi", "de pe alt telefon",
        ]
        if not known_contact:
            if (any(n in text_norm for n in new_num_tokens) and has_family_mention) or any(
                n in text_norm for n in ["numarul nou", "numar nou", "noul numar", "mi s-a stricat telefonul", "mi-am schimbat numarul", "mi-am pierdut telefonul", "cartela unui coleg"]
            ):
                add_flag("RF_NEW_NUMBER")

        # -------------------------------------------------------------
        # 2. RF_IMPERSONATION (15 pts)
        # -------------------------------------------------------------
        claims_org = False
        if "cumparator" not in sender_name:
            if _WORD_BOUNDARY_ORG_RX.search(text_norm) or _WORD_BOUNDARY_ORG_RX.search(sender_name):
                claims_org = True

        too_good_pos = -1
        for p in ["castigatorul", "tombola", "premiu"]:
            pos = text_norm.find(p)
            if pos != -1 and (too_good_pos == -1 or pos < too_good_pos):
                too_good_pos = pos

        org_match = _WORD_BOUNDARY_ORG_RX.search(text_norm)
        org_pos = org_match.start() if org_match else (0 if claims_org else -1)

        if claims_org and (too_good_pos == -1 or (org_pos != -1 and org_pos < too_good_pos)) and not is_safety_or_branch_notice:
            add_flag("RF_IMPERSONATION")

        # -------------------------------------------------------------
        # 3. RF_TOO_GOOD (20 pts)
        # -------------------------------------------------------------
        has_prize_or_hype = any(p in text_norm for p in [
            "castigatorul", "ati fost ales castigatorul", "ati castigat", "ai castigat",
            "tombola", "premiu", "premiul", "castiguri garantate", "profit garantat",
            "leac miraculos", "formula unica", "topeste instant", "nanotehnologic",
            "vindecare garantata", "campanie subventionata", "100% natural",
            "fara niciun risc", "bani usor", "dublat banii", "si-au dublat",
        ]) or bool(re.search(
            r"\b(?:primiti|primesti|castigati|castigi)\s+(?:un\s+)?(?:voucher|bonus|cadou|\d[\d.,]*\s*(?:lei\b|ron\b|eur\b|euro\b|€|\$))|"
            r"\bvoucher\s+de\s+\d|"
            r"\bfelicitari\b(?:dvs\.|[^.!?]){0,60}(?:\d[\d.,]*\s*(?:lei\b|ron\b|eur\b|euro\b|€|\$)|\bprofit\b)|"
            r"\b(?:contul|soldul)\b(?:dvs\.|[^.!?]){0,35}\ba\s+ajuns\s+la\s+\d[\d.,]*\s*(?:lei\b|ron\b|eur\b|euro\b|€|\$)|"
            r"\b(?:profit|randament|castig(?:uri)?)\b[^.!?]{0,30}\b(?:garantat|constant|sigur|pe\s+(?:zi|luna|saptamana)|zilnic|lunar)\b|"
            r"\b(?:platim|castigati)\s+\d[\d.,]*\s*(?:lei\b|ron\b|eur\b|euro\b|€|\$)\s+pe\s+(?:zi|saptamana|luna)\b|"
            r"\b(?:sprijin\s+financiar|ajutor\s+financiar)\s+de\s+\d|"
            r"\b\d[\d.,]*\s*(?:lei\b|ron\b|eur\b|euro\b|€|\$)\s+pe\s+(?:zi|saptamana|luna)[^.!?]{0,20}\bgarantat\b",
            text_norm,
        ))
        has_pension_increase = any(p in text_norm for p in [
            "pensia dumneavoastra va creste", "pensia va creste",
        ])
        is_auto_voucher = ("adaugat automat in contul dvs" in text_norm and "megashop.ro" in text_norm)
        if (has_prize_or_hype or has_pension_increase) and not is_auto_voucher:
            add_flag("RF_TOO_GOOD")

        if claims_org and "RF_IMPERSONATION" not in flags and not is_safety_or_branch_notice:
            add_flag("RF_IMPERSONATION")

        # -------------------------------------------------------------
        # 4. RF_THREAT (15 pts)
        # -------------------------------------------------------------
        threat_patterns = [
            "cardul dvs. a fost blocat", "cardul a fost blocat", "contul a fost blocat",
            "blocat temporar", "trimite virusi", "calculatorul dvs trimite virusi",
            "amenda", "dosar penal", "suspendare cont", "va fi sters",
            "mi-au blocat contul", "mi s-a blocat salariul", "contul blocat", "card blocat",
            "tranzactie suspecta", "contul dvs a fost suspendat", "va vom bloca contul",
            "riscati", "infarct", "atac cerebral", "paralizie", "vasele sunt infundate",
            "infectat cu un virus", "infectat", "hackerii", "executarea silita", "executare silita",
            "vrea sa va goleasca contul", "este retinut", "mandat de", "poprire",
            "sechestrul", "sechestru", "frauda pe cont", "eroare grava", "va sista furnizarea",
        ]
        has_regex_threat = bool(re.search(
            r"\b(?:(?:card|cont)(?:ul)?\s+(?:dvs\.?\s+|dumneavoastra\s+)?a\s+fost\s+(?:blocat|suspendat|restrictionat|compromis)|citatie|mandat\s+de|retinu[t]|inchisoare|goleasca\s+contul)\b",
            text_norm,
        ))
        if (any(p in text_norm for p in threat_patterns) or has_regex_threat) and not is_safety_or_branch_notice:
            add_flag("RF_THREAT")

        # -------------------------------------------------------------
        # 5. RF_REMOTE_ACCESS (35 pts)
        # -------------------------------------------------------------
        remote_tools = [
            "anydesk", "teamviewer", "quicksupport", "ultraviewer",
            "ammyy", "remote desktop", "logmein", "supremo", "rustdesk",
        ]
        has_tool = any(t in text_norm for t in remote_tools)
        has_remote_action = any(p in text_norm for p in [
            "acces de la distanta", "ajuta de la distanta", "control la distanta",
            "instalati programul", "descarcati aplicatia de suport", "descarcati teamviewer",
            "instalati va rog aplicatia anydesk", "partajare a ecranului", "partajare ecran",
            "sa va vad desktopul",
        ])
        if (has_tool or (has_remote_action and ("instalati" in text_norm or "descarcati" in text_norm or "oferiti" in text_norm))) and not is_safety_or_branch_notice:
            add_flag("RF_REMOTE_ACCESS")

        # -------------------------------------------------------------
        # 6. RF_PAYMENT_REQUEST (25 pts)
        # -------------------------------------------------------------
        has_zero_lei = bool(re.search(r"ramburs\s*:\s*0\s*lei", text_norm))
        is_past_confirmation = any(p in text_norm for p in [
            "a fost efectuata", "a fost efectuata cu succes", "ati efectuat o plata", "a fost autorizata",
            "tranzactie reusita", "plata a fost inregistrata", "a fost detectata",
            "incercare de plata", "plata a fost aprobata", "a fost aprobata",
            "a fost platita", "a fost platit", "platita cu succes", "a fost achitata", "a fost alimentat",
        ])
        is_in_person_counter = ("la casierie" in text_norm or "depozitul local" in text_norm)

        asks_payment = any(p in text_norm for p in [
            "achitati taxa", "platiti taxa", "taxa de reprogramare", "taxa de deblocare",
            "taxa de activare", "o taxa de", "plata transport", "taxa de transport",
            "transfer de", "faci tu un transfer", "fa-mi un transfer", "trimite-mi bani",
            "achitati suma", "poti sa-mi faci", "poti sa mi transferi", "transfera-mi", "transfera mi",
            "tre sa platesc", "trebuie sa platesc taxa", "facem plata", "sa facem plata",
            "pay the", "customs fee", "western union", "moneygram", "carduri cadou", "card cadou",
            "paysafe", "card preplatit", "avans de activare", "avansul de activare",
            "retrageti toti banii", "dati-i colegului", "dati banii", "pe contul asta",
            "depuneti o garantie", "o garantie de", "trimitei pe contul asta", "trebuie dati",
            "sa ia banii", "cont de siguranta", "cont tampon", "cont protejat", "trebuie platita o cautiune",
        ]) or bool(re.search(
            r"\b(?:depuneti|depui|depune|investiti|investeste)\b(?:\s+\S+){0,3}\s+(?:\d|doar\s+\d|o\s+garantie|bani|suma)|"
            r"\b(?:mutati|muta|transferati)\s+(?:\S+\s+){0,3}(?:banii|economiile)\b|"
            r"\b(?:un\s+)?depozit\s+(?:bancar|initial|minim|de\s+\d)|"
            r"\b(?:asigurare|garantie|cautiune|avans(?:ul)?)\s+de\s+\d[\d.,]*\s*(?:lei\b|ron\b|eur\b|euro\b|€|\$)|"
            r"\b(?:trimit|vine)\s+(?:un\s+)?(?:om|coleg|curier)\s+sa(?:-i)?\s+(?:ia|ridice|preia)\s+(?:banii|chiar\s+acum)",
            text_norm,
        ))
        # General money request: an IMPERATIVE "send / pay / deposit / transfer" verb followed by an amount with a
        # currency, or by a destination account/IBAN — e.g. "trimiteti 1000 RON in contul REV1123". Past forms
        # ("v-am trimis 1000 lei", "am platit") deliberately do not match.
        asks_transfer = bool(re.search(
            r"\b(?:trimiteti|trimite|trimiti|trimitei|trimite-mi|trimiteti-ne|trimite-ne|depuneti|virati|"
            r"transferati|platiti|achitati|alimentati)\b"
            r"(?:[^.!?]{0,60}?\b[1-9]\d*(?:[.,]\d+)*\s*(?:lei|ron|euro|eur)\b|[^.!?]{0,60}?[1-9]\d*\s*(?:€|\$)"
            r"|[^.!?]{0,60}?\b(?:in|pe|catre)\s+(?:contul|iban(?:-ul)?)\b)",
            text_norm,
        ))
        if asks_transfer:
            asks_payment = True
        has_amount = bool(re.search(r"\b[1-9]\d*(?:[.,]\d+)?\s*(?:lei\b|ron\b|euro\b|eur\b|€|\$)", text_norm))
        has_pay_verb = bool(re.search(
            r"\b(?:platit[ae]?|platiti|platim|platesc|platesti|achitat[ae]?|achitati|achita|achitam|"
            r"transferat[ae]?|transferati|transfera|transferi|virat[ae]?|virati|vireaza|"
            r"donati|doneaza|donam|pay)\b",
            text_norm,
        ))

        if not has_zero_lei and not is_past_confirmation and not is_in_person_counter and not is_safety_or_branch_notice:
            if asks_payment or (has_pay_verb and has_amount and "am platit" not in text_norm and "a platit" not in text_norm):
                add_flag("RF_PAYMENT_REQUEST")

        # -------------------------------------------------------------
        # 7. RF_SUSPICIOUS_CONTACT (25 pts)
        # -------------------------------------------------------------
        if self.contact_verifier.check_suspicious_contact(message_text, sender_info):
            add_flag("RF_SUSPICIOUS_CONTACT")

        # -------------------------------------------------------------
        # 8. RF_DATA_REQUEST (30 pts)
        # -------------------------------------------------------------
        is_failed_pin_notice = ("introduceri gresite ale pin-ului" in text_norm or "introduceri gresite" in text_norm)
        is_building_reception = ("receptie" in text_norm and "acces" in text_norm)

        asks_card = any(p in text_norm for p in [
            "datele cardului", "numarul cardului", "numarul de card",
            "codul cvv", "datele de autentificare", "completati datele",
            "introduceti datele", "poza cu buletinul", "copie buletin",
            "datele bancare", "detaliile cardului", "numele complet",
            "data expirarii", "seria de ci", "seria si numarul",
            "validati cardul", "soldul disponibil",
        ]) or bool(re.search(r"\b(?:cvv|cvc|pin(?:-ul)?|parola|cnp(?:-ul)?)\b", text_norm))

        asks_bank_login = any(p in text_norm for p in [
            "intrati in contul de banca", "autentificati-va in cont", "logati-va in aplicatie",
        ])
        if (asks_card or asks_bank_login) and not is_safety_or_branch_notice and not is_building_reception and not is_failed_pin_notice:
            add_flag("RF_DATA_REQUEST")

        # -------------------------------------------------------------
        # 9. RF_CODE_REQUEST (35 pts)
        # -------------------------------------------------------------
        prior_code_context = False
        if context_history:
            prior_text = deobfuscate_for_detection(" ".join(
                str(m.get("text") or "") for m in context_history if isinstance(m, dict)
            ))
            prior_code_context = bool(re.search(r"\b(?:cod(?:ul)?|otp|cifre)\b", prior_text))

        asks_code = any(p in text_norm for p in [
            "trimite-mi codul", "trimite mi codul", "mi-l poti trimite inapoi",
            "cititi-mi codul", "pe care mi-l cititi", "spuneti codul", "spune-mi codul",
            "da-mi codul", "trimite-mi-l", "trimiteti codul", "introduceti codul",
            "mi-l cititi", "codul primit", "cod de confirmare", "cod de 6 cifre",
            "ce cifre apar",
        ]) or bool(re.search(
            r"\b(?:cod(?:ul)?|otp|cifre(?:le)?)\b[^.!?]{0,45}\b(?:trimit|citit|spun|dat|dict|comunic|da|dai|dati|zi|apar)\w*|"
            r"\b(?:sa\s+(?:mi|ne)\s+|va\s+rog\s+sa\s+(?:mi|ne)\s+)?(?:cititi|comunicati|transmiteti|spuneti|dati|trimiteti)\b[^.!?]{0,40}\b(?:cod(?:ul)?|cifre(?:le)?|otp)\b|"
            r"\b(?:zi-mi-l|da-mi-l|spune-mi-l|citeste-mi-l|mi-l\s+(?:poti|puteti)\s+(?:da|spune|trimite|citi|zice)|sa\s+mi-l\s+(?:dai|dati|spui|trimiti))\b",
            text_norm,
        )) or (
            prior_code_context and bool(re.search(
                r"\b(?:trimite-l|spune-l|citeste-l|da-l|zi-l|mi-l\s+(?:dai|spui|trimiti|citesti)|sa\s+mi-l\s+(?:dai|spui|trimiti))\b",
                text_norm,
            ))
        )
        if asks_code and not is_safety_or_branch_notice and "codul de confirmare este" not in text_norm:
            add_flag("RF_CODE_REQUEST")

        # -------------------------------------------------------------
        # 10. RF_URGENCY (15 pts)
        # -------------------------------------------------------------
        has_action_urgency = any(p in text_norm for p in [
            "in 24h", "in 24 de ore", "termen de 24", "urgent", "urgnt", "expira intr-o ora",
            "expira", "imediat", "chiar acum", "azi", "astazi", "doar azi",
            "trebuie sa platesc azi", "sa platesc azi", "cat mai repede",
            "grabiti-va", "grabeste-te", "pana la 30.11", "pana la data",
            "prea tarziu", "pana maine", "diseara", "pana diseara", "repede", "rpede",
            "nu amanati", "nu amana",
        ]) or bool(re.search(
            r"\bin\s+\d+\s*(?:h|de\s+)?ore\b|\bincepeti\b[^.!?]{0,20}\bde\s+maine\b|"
            # General deadlines: "mai aveti 5 ore", "aveti doar 2 zile", "in urmatoarele 30 de minute"
            r"\b(?:mai\s+(?:aveti|ai|avem)|(?:aveti|ai)\s+(?:doar|numai))\s+(?:doar\s+|numai\s+)?"
            r"(?:\d+|o|un|doua|trei)\s*(?:de\s+)?(?:h|ore|ora|minute|min|zile|zi)\b|"
            r"\bin\s+(?:urmatoarele|maxim|cel\s+mult)\s+\d+\s*(?:de\s+)?(?:h|ore|ora|minute|min|zile)\b",
            text_norm,
        ))
        if has_action_urgency and not is_safety_or_branch_notice:
            add_flag("RF_URGENCY")

        # -------------------------------------------------------------
        # 11. RF_SECRECY (20 pts)
        # -------------------------------------------------------------
        if any(p in text_norm for p in [
            "nu-i spune", "nu i spune", "nu-i zice", "nu spune lui", "nu spune nimanui",
            "nu mai spune nimanui", "nu vorbi cu nimeni", "sa ramana intre noi", "in secret",
            "se enerveaza", "secretul nostru", "ancheta e secreta", "nu sunati pe nimeni",
            "nu anuntati pe nimeni", "nu anuntati politia", "nu contactati pe nimeni",
            "ii faceti mai rau", "sa nu afle nimeni", "nu spuneti nimic la banca",
        ]) or bool(re.search(
            r"\bsecret(?:ul|a)?\b|\bnu\s+(?:ii|i|le)?\s*spune(?:ti)?\s+(?:nimic\s+)?(?:nimanui|parintilor|familiei|tatalui|mamei|copiilor|bancii)\b",
            text_norm,
        )):
            add_flag("RF_SECRECY")

        # -------------------------------------------------------------
        # 12. RF_EMOTIONAL_PRESSURE (10 pts)
        # -------------------------------------------------------------
        if any(p in text_norm for p in [
            "am facut un accident", "sunt la spital", "la urgenta", "a cazut pe scari",
            "sunt disperat", "te implor", "din suflet", "ajuta-ma te rog", "ajuta-ma", "ajuta ma",
            "nenorocire", "sunt la politie", "misiune militara", "sunt blocat", "ascund adevarul",
            "dependenta de pastile", "situatie grava", "a lovit o femeie", "la inchisoare",
            "sa nu intre la inchisoare", "doar tu ma poti ajuta", "armata nu ma lasa",
            "sufletul meu pereche", "suflet drag", "sa ne putem revedea", "este retinut",
        ]):
            add_flag("RF_EMOTIONAL_PRESSURE")

        # -------------------------------------------------------------
        # 13. RF_CHANNEL_SWITCH (10 pts)
        # -------------------------------------------------------------
        has_switch_app = bool(re.search(
            r"\b(?:pe\s+(?:telegram|whatsapp|whats\s*app|signal|viber|discord|skype)|t\.me/|wa\.me/)\b",
            text_norm,
        ))
        if has_switch_app or any(p in text_norm for p in [
            "vorbim pe telegram", "muta-te pe", "hai pe telegram",
            "continuam pe telegram", "scrie-mi urgent pe telegram",
        ]):
            add_flag("RF_CHANNEL_SWITCH")

        # -------------------------------------------------------------
        # 14. TIER-6 DUAL-GATED NEURAL+LINEAR & SEMANTIC ENSEMBLE BOOST
        # -------------------------------------------------------------
        if not is_safety_or_branch_notice and not is_past_confirmation and not is_in_person_counter:
            semantic_scores = self.semantic_nli.evaluate_semantic_resonance(message_text)
            ml_probs = self.semantic_nli.predict_ml_flag_probs(message_text)
            risk_prob = self.semantic_nli.predict_risk_intent_prob(message_text)

            for context_flag in (
                "RF_THREAT",
                "RF_TOO_GOOD",
                "RF_EMOTIONAL_PRESSURE",
                "RF_URGENCY",
                "RF_SECRECY",
                "RF_CHANNEL_SWITCH",
            ):
                sem_val = semantic_scores.get(context_flag, 0.0)
                ml_val = ml_probs.get(context_flag, 0.0)
                if sem_val >= 0.70 or (risk_prob >= 0.72 and ml_val >= 0.85):
                    add_flag(context_flag)

            # High-confidence ML rescue on typo-corrupted or paraphrased core request flags
            if risk_prob >= 0.75:
                for req_flag in ("RF_CODE_REQUEST", "RF_REMOTE_ACCESS", "RF_DATA_REQUEST", "RF_PAYMENT_REQUEST"):
                    if ml_probs.get(req_flag, 0.0) >= 0.86:
                        add_flag(req_flag)

        return flags

    def extract_evidence_spans(self, message_text: str, detected_flags: List[str]) -> List[Tuple[str, Tuple[int, int]]]:
        """
        Extracts 1-to-1 aligned character [start, end) spans in original message_text
        for UI/backend highlighting.
        """
        if not message_text or not detected_flags:
            return []
        norm_exact = normalize_preserve_length(message_text)
        span_patterns = {
            "RF_CODE_REQUEST": r"\b(?:cod\w*|otp)\b",
            "RF_REMOTE_ACCESS": r"\b(?:anydesk|teamviewer|quicksupport|ultraviewer|rustdesk|la distanta)\b",
            "RF_DATA_REQUEST": r"\b(?:datele cardului|numarul cardului|cvv|cvc|pin|parola|cnp|buletin\w*)\b",
            "RF_PAYMENT_REQUEST": r"\b(?:achit\w*|plat\w*|transfer\w*|depun\w*|taxa|garantie|cautiune|western union|carduri cadou)\b",
            "RF_SUSPICIOUS_CONTACT": r"(?:https?://\S+|[a-z0-9-]+\.(?:com|net|info|online|site|org|biz)\S*|03\d{2}[\s\d]+)",
            "RF_NEW_NUMBER": r"\b(?:numar\w* nou|mi s-a stricat telefonul|mi-am pierdut telefonul)\b",
            "RF_SECRECY": r"\b(?:nu-i spune|nu spune|nu sunati|nu anuntati|secret\w*|intre noi)\b",
            "RF_TOO_GOOD": r"\b(?:castig\w*|premiu\w*|tombola|garantat|voucher|va creste|miracul\w*|formula unica)\b",
            "RF_IMPERSONATION": r"\b(?:banca\w*|curier\w*|anaf|megashop|suport\w*|casa de pensii|politi\w*|procuror\w*|ghiseul\w*)\b",
            "RF_URGENCY": r"\b(?:urgent|24\s*(?:h|de ore)|expira|imediat|astazi|azi|grabit\w*)\b",
            "RF_THREAT": r"\b(?:blocat\w*|virusi|infectat|amenda|dosar penal|compromis|retinut|inchisoare|infarct)\b",
            "RF_EMOTIONAL_PRESSURE": r"\b(?:accident|spital|te implor|ajuta-ma|iubirea mea|sufletul meu)\b",
            "RF_CHANNEL_SWITCH": r"\b(?:telegram|whatsapp|signal|viber)\b",
        }
        out: List[Tuple[str, Tuple[int, int]]] = []
        for flag in detected_flags:
            pat = span_patterns.get(flag)
            if not pat:
                continue
            m = re.search(pat, norm_exact, re.IGNORECASE)
            if m:
                out.append((flag, (m.start(), m.end())))
        return out
