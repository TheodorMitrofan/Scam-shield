"""scam_detector — local scam detection for Scam Shield (no cloud LLMs, nothing leaves the machine).

Public API (CLAUDE.md §4.2):
    load(model_dir=None) -> bool          # load fine-tuned model once; False = rules-only mode
    analyze(scenario: dict) -> dict       # AnalysisResult
    analyze_text(text, channel="sms", ...) -> dict
"""
import os

from . import fusion, warnings
from .catalog import FLAG_ORDER, get_catalog

__all__ = ["load", "analyze", "analyze_text", "model_loaded", "FLAG_ORDER"]

_MODEL = None
_LOAD_ATTEMPTED = False


def load(model_dir: str | None = None) -> bool:
    """Load the fine-tuned model (if weights exist). Safe to call many times."""
    global _MODEL, _LOAD_ATTEMPTED
    _LOAD_ATTEMPTED = True
    if os.environ.get("SCAM_RULES_ONLY") == "1":
        _MODEL = None
        return False
    try:
        from .model import ScamModel
        _MODEL = ScamModel.try_load(model_dir)
    except Exception:
        _MODEL = None
    return _MODEL is not None


def model_loaded() -> bool:
    return _MODEL is not None


def analyze(scenario: dict) -> dict:
    if not _LOAD_ATTEMPTED:
        load()
    if not isinstance(scenario, dict):
        scenario = {}
    res = fusion.analyze_core(scenario, model=_MODEL)
    res["warning"] = warnings.build(res, scenario)
    res.pop("_claim_orgs", None)
    res.pop("_sender_org", None)
    res["engine"] = "rules+model" if _MODEL is not None else "rules"
    return res


def analyze_text(text: str, channel: str = "sms", sender_name=None, sender_address=None,
                 known_contact: bool = False, sid: str = "PASTE") -> dict:
    """Pasted text: blank lines or lines starting with 'Reader:'/'Eu:' become separate messages."""
    msgs = []
    blocks = [b for b in (text or "").replace("\r", "").split("\n\n") if b.strip()] or [text or ""]
    for i, b in enumerate(blocks, 1):
        frm = "sender"
        s = b.strip()
        for p in ("Reader:", "reader:", "Eu:", "eu:", "Cititor:"):
            if s.startswith(p):
                frm, s = "reader", s[len(p):].strip()
        msgs.append({"n": i, "from": frm, "text": s})
    scenario = {"id": sid, "channel": channel,
                "sender": {"name": sender_name, "address": sender_address, "known_contact": known_contact},
                "messages": msgs}
    return analyze(scenario)
