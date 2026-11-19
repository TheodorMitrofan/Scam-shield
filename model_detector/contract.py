from __future__ import annotations
"""Shape a raw `scam_detector.analyze()` result into the AnalysisResult contract (CLAUDE.md §4.2),
exactly as `backend/app/schemas/analysis.py` validates it.

- flags_by_message[].flags = flags FIRST detected in message n (the engine's `new_flags`);
  the full per-message set stays available as `all_flags`.
- evidence keeps only items with a character span (model-only flags have no span) and drops the
  internal `source`/`p` fields into `evidence_source` so the backend DTO validates cleanly.
"""


def to_contract(raw: dict, scenario: dict | None) -> dict:
    fbm = []
    for m in raw.get("flags_by_message") or []:
        fbm.append({"n": m["n"], "flags": m.get("new_flags", m.get("flags", [])), "all_flags": m.get("flags", []),
                    "score_after": m["score_after"]})
    evidence = []
    for e in raw.get("evidence") or []:
        span = e.get("span")
        if not span or len(span) != 2:
            continue
        evidence.append({"n": e["n"], "flag": e["flag"], "span": [int(span[0]), int(span[1])],
                         "source": e.get("source", "rule")})
    out = {
        "id": str((scenario or {}).get("id") or raw.get("id") or "PASTE"),
        "verdict": raw["verdict"],
        "scam_type": raw["scam_type"],
        "risk_score": raw["risk_score"],
        "first_alert": raw.get("first_alert"),
        "red_flags": raw.get("red_flags", []),
        "flags_by_message": fbm,
        "warning": raw.get("warning") or {"ro": ""},
        "evidence": evidence,
        "engine": raw.get("engine"),
    }
    if raw.get("model_type"):
        out["model_type"] = raw["model_type"]  # transparency only, never used for the decision
    return out
