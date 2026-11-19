import json
import os
from typing import Dict, Optional, Union
from .catalog import Catalog
from .sequential_engine import SequentialEngine
from .warning_generator import WarningGenerator

class ScamShieldPipeline:
    def __init__(self, catalog_path: Optional[str] = None):
        self.catalog = Catalog(catalog_path)
        self.engine = SequentialEngine(self.catalog)
        self.warning_generator = WarningGenerator()

    def analyze_scenario(self, scenario_data: Dict) -> Dict:
        """
        Takes a scenario dictionary (matching standard input format) and performs
        full end-to-end multi-signal detection.
        """
        result = self.engine.process_scenario(scenario_data)
        warnings_dict = self.warning_generator.generate_bilingual_warning(result)
        result["warning"] = warnings_dict["ro"]
        result["warning_en"] = warnings_dict["en"]
        return result

    @staticmethod
    def to_backend_contract(result: Dict) -> Dict:
        """
        Formats analyze_scenario() output to match origin/main AnalysisResult schema.
        """
        return {
            "id": result["id"],
            "verdict": result["verdict"],
            "scam_type": result["scam_type"],
            "risk_score": result["risk_score"],
            "first_alert": result["first_alert"],
            "red_flags": result["red_flags"],
            "flags_by_message": result.get("flags_by_message", []),
            "evidence": result.get("evidence", []),
            "warning": {
                "ro": result.get("warning", ""),
                "en": result.get("warning_en", ""),
            },
        }

    def analyze_file(self, file_path: str) -> Dict:
        """
        Reads a scenario JSON file and analyzes it.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.analyze_scenario(data)

    def analyze_raw_text(
        self,
        text: str,
        channel: str = "sms",
        sender_name: Optional[str] = None,
        sender_address: Optional[str] = None,
        known_contact: bool = False
    ) -> Dict:
        """
        Convenience method to analyze a pasted text message.
        """
        scenario = {
            "id": "CUSTOM",
            "channel": channel,
            "sender": {
                "name": sender_name,
                "address": sender_address,
                "known_contact": known_contact
            },
            "messages": [
                {
                    "n": 1,
                    "from": "sender",
                    "text": text
                }
            ]
        }
        return self.analyze_scenario(scenario)
