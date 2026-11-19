"""Compare detector output with an answer key and compute the brief's accuracy points.

python -m scam_detector.evaluate <folder> <expected.csv> [--rules-only] [--verbose]

Points per scenario (brief): verdict 3, type 2, first alert 2 for scam threads (exact / window,
1 if one message late), -3 extra for every SCAM/SUSPICIOUS predicted as SAFE.
"""
import argparse
import csv
import sys

from .cli import run

# accepted first-alert windows from the brief ("3 (accepted window 3–5)")
WINDOWS = {"V11": (3, 5)}


def score_row(exp, got):
    pts, mx = 0, 5
    pts += 3 if got["verdict"] == exp["verdict"] else 0
    pts += 2 if got["scam_type"] == exp["scam_type"] else 0
    fa_ok = None
    if exp["verdict"] != "SAFE" and exp["first_alert"]:
        mx += 2
        e = int(exp["first_alert"])
        lo, hi = WINDOWS.get(exp["id"], (e, e))
        g = got["first_alert"]
        if g is not None and lo <= g <= hi:
            pts += 2
            fa_ok = True
        elif g is not None and g == hi + 1:
            pts += 1
            fa_ok = False
        else:
            fa_ok = False
    if exp["verdict"] != "SAFE" and got["verdict"] == "SAFE":
        pts -= 3
    return pts, mx, fa_ok


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("expected")
    ap.add_argument("--rules-only", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    a = ap.parse_args(argv)
    results, model_on = run(a.folder, a.rules_only)
    got = {r["id"]: r for r in results}
    with open(a.expected, encoding="utf-8-sig") as f:
        expected = list(csv.DictReader(f))
    tot = mx = 0
    exact = {"verdict": 0, "type": 0, "first_alert": 0, "flags": 0, "score": 0}
    print(f"engine: {'rules+model' if model_on else 'rules only'}")
    for e in expected:
        g = got.get(e["id"])
        if g is None:
            print(f"{e['id']}: MISSING")
            continue
        p, m, fa_ok = score_row(e, g)
        tot, mx = tot + p, mx + m
        ef = set(filter(None, e["red_flags"].split(";")))
        gf = set(g["red_flags"])
        checks = {
            "verdict": g["verdict"] == e["verdict"],
            "type": g["scam_type"] == e["scam_type"],
            "first_alert": (str(g["first_alert"] or "") == e["first_alert"]) or bool(fa_ok),
            "flags": ef == gf,
            "score": int(e["risk_score"]) == g["risk_score"],
        }
        for k, v in checks.items():
            exact[k] += int(v)
        bad = [k for k, v in checks.items() if not v]
        status = "OK " if not bad else "XX "
        print(f"{status}{e['id']}  {p}/{m}  got {g['verdict']}/{g['scam_type']}/{g['risk_score']}/fa={g['first_alert']}"
              + (f"   MISMATCH {bad}  exp {e['verdict']}/{e['scam_type']}/{e['risk_score']}/fa={e['first_alert']}" if bad else ""))
        if bad and "flags" in bad:
            print(f"      missing {sorted(ef - gf)}  extra {sorted(gf - ef)}")
        if a.verbose:
            for fm in g["flags_by_message"]:
                print(f"      [{fm['n']}] {fm['flags']} -> {fm['score_after']}")
            print(f"      {g['warning']['ro']}")
    n = len(expected)
    print("-" * 60)
    print("  ".join(f"{k} {v}/{n}" for k, v in exact.items()))
    print(f"brief accuracy points: {tot}/{mx}  -> {30 * max(tot, 0) / mx:.1f}/30")
    return 0 if tot == mx else 1


if __name__ == "__main__":
    sys.exit(main())
