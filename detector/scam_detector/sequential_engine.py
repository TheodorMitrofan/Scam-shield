from typing import Dict, List, Optional, Set
from .catalog import Catalog
from .red_flags import RedFlagDetector
from .scam_classifier import ScamClassifier
from .text_utils import normalize_text


class SequentialEngine:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.scam_classifier = ScamClassifier()
        self.red_flag_detector = RedFlagDetector(
            catalog,
            model_bundle=self.scam_classifier.get_model_bundle(),
        )

    def process_scenario(self, scenario_data: Dict) -> Dict:
        """
        Processes a full scenario JSON object.
        Returns a dictionary with:
          - id
          - verdict: SAFE | SUSPICIOUS | SCAM
          - scam_type
          - risk_score: 0-100
          - first_alert: int or None
          - red_flags: List[str] in exact order of appearance
          - flags_by_message: List[Dict] compatible with backend DTO
          - evidence: List[Dict] char [start, end] spans per message
          - messages_analysis: List[Dict] (step-by-step trace)
        """
        if not isinstance(scenario_data, dict):
            scenario_data = {}
        raw_id = scenario_data.get("id")
        scenario_id = str(raw_id) if raw_id is not None else "UNKNOWN"
        sender_info = scenario_data.get("sender")
        if not isinstance(sender_info, dict):
            sender_info = {}
        raw_messages = scenario_data.get("messages")
        messages = [m for m in raw_messages if isinstance(m, dict)] if isinstance(raw_messages, list) else []

        # Pass 1: Collect message flags across conversation
        history: List[Dict] = []
        full_text_parts: List[str] = []
        step_flags_list = []

        for msg in messages:
            raw_n = msg.get("n")
            n = raw_n if isinstance(raw_n, int) and raw_n >= 1 else (len(history) + 1)
            from_who = msg.get("from", "sender")
            text = str(msg.get("text") or "")
            full_text_parts.append(text)

            is_from_reader = (from_who == "reader")
            new_flags = self.red_flag_detector.detect_flags_for_message(
                message_text=text,
                sender_info=sender_info,
                context_history=history,
                is_from_reader=is_from_reader,
            )
            step_flags_list.append((n, from_who, text, new_flags))
            history.append(msg)

        # Aggregate all unique flags
        all_detected_flags_set: Set[str] = set()
        for _, _, _, flags in step_flags_list:
            all_detected_flags_set.update(flags)

        # Trap filter: genuine official communication without hostile requests or fake links/phones
        has_hostile_action = any(f in all_detected_flags_set for f in [
            "RF_SUSPICIOUS_CONTACT", "RF_DATA_REQUEST", "RF_PAYMENT_REQUEST",
            "RF_CODE_REQUEST", "RF_REMOTE_ACCESS", "RF_NEW_NUMBER", "RF_SECRECY",
            "RF_TOO_GOOD",
        ])

        sender_addr = sender_info.get("address") or ""
        sender_name = sender_info.get("name") or ""
        norm_s = normalize_text(f"{sender_addr} {sender_name}").replace(" ", "")
        is_official_claimed = any(
            normalize_text(org["organisation"]).replace(" ", "") in norm_s
            for org in self.catalog.official_contacts
        )

        is_genuine = False
        if not has_hostile_action and "RF_SUSPICIOUS_CONTACT" not in all_detected_flags_set:
            if is_official_claimed and all_detected_flags_set.issubset({"RF_IMPERSONATION", "RF_THREAT", "RF_URGENCY"}):
                is_genuine = True
            elif all_detected_flags_set == {"RF_IMPERSONATION"}:
                is_genuine = True

        # Pass 2: Calculate cumulative score, first_alert, and evidence spans
        accumulated_flags: List[str] = []
        first_alert: Optional[int] = None
        messages_analysis = []
        flags_by_message = []
        evidence = []

        for n, from_who, text, new_flags in step_flags_list:
            valid_new_flags = []
            for f in new_flags:
                if is_genuine and f in {"RF_IMPERSONATION", "RF_THREAT", "RF_URGENCY", "RF_TOO_GOOD"}:
                    continue
                if f not in accumulated_flags:
                    accumulated_flags.append(f)
                    valid_new_flags.append(f)

            current_score = min(100, sum(self.catalog.red_flag_points[f] for f in accumulated_flags))

            if current_score >= 25 and first_alert is None:
                first_alert = n

            if valid_new_flags:
                for flag_code, (start_idx, end_idx) in self.red_flag_detector.extract_evidence_spans(text, valid_new_flags):
                    evidence.append({
                        "n": n,
                        "flag": flag_code,
                        "span": [start_idx, end_idx],
                        "source": "rule",
                    })

            flags_by_message.append({
                "n": n,
                "flags": valid_new_flags,
                "all_flags": list(accumulated_flags),
                "score_after": current_score,
            })

            messages_analysis.append({
                "n": n,
                "from": from_who,
                "text": text,
                "new_flags": valid_new_flags,
                "cumulative_score": current_score,
                "is_first_alert": (first_alert == n),
            })

        total_score = min(100, sum(self.catalog.red_flag_points[f] for f in accumulated_flags))
        verdict = self.catalog.get_verdict(total_score)

        full_text = " ".join(full_text_parts)
        scam_type = self.scam_classifier.classify(
            red_flags=set(accumulated_flags),
            full_text=full_text,
            sender_info=sender_info,
        )

        if verdict == "SAFE":
            scam_type = "NONE"
            first_alert = None
        elif scam_type == "NONE":
            scam_type = "OTHER"

        return {
            "id": scenario_id,
            "verdict": verdict,
            "scam_type": scam_type,
            "risk_score": total_score,
            "first_alert": first_alert,
            "red_flags": accumulated_flags,
            "flags_by_message": flags_by_message,
            "evidence": evidence,
            "messages_analysis": messages_analysis,
        }
