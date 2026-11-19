"""Fine-tuned multi-task transformer (local inference only).

One encoder (XLM-RoBERTa) + two heads:
  * flag head  — multi-label sigmoid over MODEL_FLAGS, one prediction per sender message (with context)
  * type head  — softmax over the official scam types, one prediction per thread
Probabilities are temperature-calibrated (temperatures stored in meta.json by ml/train.py).

Weights live in MODEL_DIR (default <repo>/models/scam-bert, gitignored). If they are missing,
ScamModel.try_load() returns None and the detector silently runs rules-only.
"""
import json
import os
from pathlib import Path

MODEL_FLAGS = [
    "RF_CODE_REQUEST", "RF_REMOTE_ACCESS", "RF_DATA_REQUEST", "RF_PAYMENT_REQUEST", "RF_NEW_NUMBER", "RF_SECRECY",
    "RF_TOO_GOOD", "RF_URGENCY", "RF_THREAT", "RF_EMOTIONAL_PRESSURE", "RF_CHANNEL_SWITCH",
]
TYPES = ["BANK_IMPERSONATION", "COURIER_FEE", "AUTHORITY_IMPERSONATION", "FAMILY_EMERGENCY", "TECH_SUPPORT", "MARKETPLACE",
         "ACCOUNT_TAKEOVER", "INVESTMENT", "ROMANCE", "JOB_OFFER", "PRIZE_LOTTERY", "OTHER", "NONE"]
DEFAULT_DIR = Path(__file__).resolve().parents[2] / "models" / "scam-bert"
MIN_MODEL_THRESHOLD = 0.9   # model may only ADD a flag when it is very sure


# ---------------------------------------------------------------- input building (shared with ml/train.py)
def header(scenario: dict) -> str:
    s = scenario.get("sender") or {}
    known = "contact salvat" if s.get("known_contact") else "necunoscut"
    name = s.get("name") or ""
    addr = s.get("address") or ""
    return f"[{scenario.get('channel') or 'sms'}] [{known}] {name} {addr}".strip()


def message_inputs(scenario: dict, ctx_msgs: int = 2):
    """[(n, text, pair)] for each sender message: text = the message, pair = header + previous sender messages."""
    out, prev = [], []
    for i, m in enumerate(scenario.get("messages") or []):
        if not isinstance(m, dict):
            continue
        t = str(m.get("text") or "")
        if (m.get("from") or "sender") != "sender":
            continue
        pair = header(scenario) + " | " + " | ".join(prev[-ctx_msgs:])
        out.append((m.get("n") or i + 1, t, pair))
        prev.append(t)
    return out


def thread_input(scenario: dict) -> str:
    msgs = [str(m.get("text") or "") for m in scenario.get("messages") or [] if isinstance(m, dict)
            and (m.get("from") or "sender") == "sender"]
    return header(scenario) + " || " + " | ".join(msgs)


# ---------------------------------------------------------------- network
def build_network(base_or_dir, n_flags, n_types):
    import torch.nn as nn
    from transformers import AutoModel

    class MultiTask(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = AutoModel.from_pretrained(base_or_dir)
            h = self.encoder.config.hidden_size
            self.drop = nn.Dropout(0.1)
            self.flag_head = nn.Linear(h, n_flags)
            self.type_head = nn.Linear(h, n_types)

        def forward(self, input_ids, attention_mask):
            out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
            cls = self.drop(out.last_hidden_state[:, 0])
            return self.flag_head(cls), self.type_head(cls)

    return MultiTask()


class ScamModel:
    def __init__(self, model_dir: Path):
        import torch
        from transformers import AutoTokenizer

        self.torch = torch
        self.dir = Path(model_dir)
        with open(self.dir / "meta.json", encoding="utf-8") as f:
            self.meta = json.load(f)
        self.flags = self.meta["flags"]
        self.types = self.meta["types"]
        self.device = "cuda" if torch.cuda.is_available() and os.environ.get("SCAM_CPU") != "1" else "cpu"
        self.tok = AutoTokenizer.from_pretrained(self.dir)
        self.net = build_network(self.dir, len(self.flags), len(self.types))
        state = torch.load(self.dir / "heads.pt", map_location="cpu")
        self.net.flag_head.load_state_dict(state["flag_head"])
        self.net.type_head.load_state_dict(state["type_head"])
        self.net.to(self.device).eval()
        self.max_len = int(self.meta.get("max_len", 160))
        self.t_flag = float(self.meta.get("temp_flag", 1.0))
        self.t_type = float(self.meta.get("temp_type", 1.0))
        self.thr = self.meta.get("thresholds", {})

    @classmethod
    def try_load(cls, model_dir=None):
        d = Path(model_dir or os.environ.get("MODEL_DIR") or DEFAULT_DIR)
        if not d.is_absolute() and not d.exists():
            d = Path(__file__).resolve().parents[2] / d
        if not (d / "meta.json").is_file() or not (d / "heads.pt").is_file():
            return None
        return cls(d)

    def threshold(self, flag: str) -> float:
        return max(MIN_MODEL_THRESHOLD, float(self.thr.get(flag, 0.5)))

    def predict(self, scenario: dict):
        torch = self.torch
        items = message_inputs(scenario)
        texts = [t for _, t, _ in items] + [thread_input(scenario)]
        pairs = [p for _, _, p in items] + [None]
        with torch.inference_mode():
            flag_probs = {}
            if items:
                enc = self.tok([t for t in texts[:-1]], [p for p in pairs[:-1]], truncation=True, max_length=self.max_len,
                               padding=True, return_tensors="pt").to(self.device)
                fl, _ = self.net(enc["input_ids"], enc["attention_mask"])
                p = torch.sigmoid(fl.float() / self.t_flag).cpu().numpy()
                for (n, _, _), row in zip(items, p):
                    flag_probs[n] = {f: float(row[j]) for j, f in enumerate(self.flags)}
            enc = self.tok([texts[-1]], truncation=True, max_length=256, padding=True, return_tensors="pt").to(self.device)
            _, tl = self.net(enc["input_ids"], enc["attention_mask"])
            tp = torch.softmax(tl.float() / self.t_type, dim=-1).cpu().numpy()[0]
            type_probs = {t: float(tp[j]) for j, t in enumerate(self.types)}
        return flag_probs, type_probs
