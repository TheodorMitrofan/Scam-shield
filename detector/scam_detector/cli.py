"""python -m scam_detector.cli <file.json|folder> [--csv out.csv] [--json] [--rules-only]"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path


def load_scenarios(path: str):
    p = Path(path)
    files = sorted(p.glob("*.json")) if p.is_dir() else [p]
    out = []
    for f in files:
        try:
            with open(f, encoding="utf-8-sig") as fh:
                d = json.load(fh)
            if isinstance(d, list):
                out.extend(d)
            else:
                out.append(d)
        except Exception as e:  # robustness: a bad file must not kill the batch
            out.append({"id": f.stem, "channel": "sms", "sender": {}, "messages": [], "_error": str(e)})
    return out


def run(path, rules_only=False):
    if rules_only:
        os.environ["SCAM_RULES_ONLY"] = "1"
    import scam_detector as sd
    sd.load()
    results = [sd.analyze(s) for s in load_scenarios(path)]
    return sorted(results, key=lambda r: r["id"]), sd.model_loaded()


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--csv")
    ap.add_argument("--json", action="store_true", help="print full JSON results")
    ap.add_argument("--rules-only", action="store_true")
    a = ap.parse_args(argv)
    results, model_on = run(a.path, a.rules_only)
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"engine: {'rules+model' if model_on else 'rules only'}   scenarios: {len(results)}")
        for r in results:
            print(f"{r['id']:<6} {r['verdict']:<10} {r['scam_type']:<24} {r['risk_score']:>3}  "
                  f"{str(r['first_alert'] or ''):<3} {';'.join(r['red_flags'])}")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "verdict", "scam_type", "risk_score", "first_alert", "red_flags"])
            for r in results:
                w.writerow([r["id"], r["verdict"], r["scam_type"], r["risk_score"], r["first_alert"] or "",
                            ";".join(r["red_flags"])])


if __name__ == "__main__":
    main()
