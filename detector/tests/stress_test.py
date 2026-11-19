"""Stress test: hand-written traps & hard cases, scored like the jury does.

    python detector/tests/stress_test.py                 # rules-only and rules+model (if weights exist), side by side
    python detector/tests/stress_test.py -v              # also print flags per message + warning for failures
    python detector/tests/stress_test.py --file other.json

Scoring per scenario (participant brief): verdict 3, type 2, first alert 2 for non-SAFE threads
(1 if one message late), -3 extra when a SCAM/SUSPICIOUS case is called SAFE.
"""
import argparse
import collections
import copy
import json
import sys
from pathlib import Path

import scam_detector as sd

HERE = Path(__file__).parent


def score(exp, got):
    types = exp["scam_type"] if isinstance(exp["scam_type"], list) else [exp["scam_type"]]
    v_ok = got["verdict"] == exp["verdict"]
    t_ok = got["scam_type"] in types
    pts, mx = (3 if v_ok else 0) + (2 if t_ok else 0), 5
    fa_ok = True
    if exp["verdict"] != "SAFE":
        mx += 2
        lo, hi = exp.get("window") or (exp["first_alert"], exp["first_alert"])
        g = got["first_alert"]
        if g is not None and lo <= g <= hi:
            pts += 2
        elif g is not None and g == hi + 1:
            pts += 1
            fa_ok = False
        else:
            fa_ok = False
    else:
        fa_ok = got["first_alert"] is None
    missed = exp["verdict"] != "SAFE" and got["verdict"] == "SAFE"
    false_alarm = exp["verdict"] == "SAFE" and got["verdict"] != "SAFE"
    if missed:
        pts -= 3
    return {"pts": pts, "max": mx, "v": v_ok, "t": t_ok, "fa": fa_ok, "missed": missed, "fa_alarm": false_alarm}


def run(data, use_model):
    saved = sd._MODEL
    if not use_model:
        sd._MODEL = None
    try:
        out = []
        for s in data:
            s = copy.deepcopy(s)
            exp, cat, note = s.pop("expected"), s.pop("category"), s.pop("note", "")
            got = sd.analyze(s)
            out.append((s, exp, cat, note, got, score(exp, got)))
        return out
    finally:
        sd._MODEL = saved


def report(name, rows, verbose):
    print(f"\n=== {name} ===")
    by_cat = collections.defaultdict(list)
    for r in rows:
        by_cat[r[2]].append(r)
    tot = mx = 0
    print(f"{'category':<18}{'n':>3}  {'verdict':>8}{'type':>7}{'alert':>7}{'missed':>8}{'f.alarm':>9}{'points':>10}")
    for cat, rs in by_cat.items():
        p = sum(r[5]["pts"] for r in rs)
        m = sum(r[5]["max"] for r in rs)
        tot, mx = tot + p, mx + m
        print(f"{cat:<18}{len(rs):>3}  {sum(r[5]['v'] for r in rs):>8}{sum(r[5]['t'] for r in rs):>7}"
              f"{sum(r[5]['fa'] for r in rs):>7}{sum(r[5]['missed'] for r in rs):>8}{sum(r[5]['fa_alarm'] for r in rs):>9}"
              f"{p:>6}/{m:<4}")
    n = len(rows)
    print(f"{'TOTAL':<18}{n:>3}  {sum(r[5]['v'] for r in rows):>8}{sum(r[5]['t'] for r in rows):>7}"
          f"{sum(r[5]['fa'] for r in rows):>7}{sum(r[5]['missed'] for r in rows):>8}{sum(r[5]['fa_alarm'] for r in rows):>9}"
          f"{tot:>6}/{mx:<4}  -> {30 * max(tot, 0) / max(mx, 1):.1f}/30")
    fails = [r for r in rows if not (r[5]["v"] and r[5]["t"] and r[5]["fa"])]
    if fails:
        print("failures:")
    for s, exp, cat, note, got, sc in fails:
        print(f"  {s['id']} [{cat}] {note}")
        print(f"      got {got['verdict']}/{got['scam_type']}/{got['risk_score']}/fa={got['first_alert']} {got['red_flags']}")
        print(f"      exp {exp['verdict']}/{exp['scam_type']}/fa={exp['first_alert']}")
        if verbose:
            for fm in got["flags_by_message"]:
                print(f"        [{fm['n']}] {fm['flags']} -> {fm['score_after']}")
            for e in got["evidence"]:
                if e["source"] == "model":
                    print(f"        model added {e['flag']} p={e.get('p')} @msg {e['n']}")
            print(f"        warning: {got['warning']['ro']}")
    return tot, mx


def main():
    for st in (sys.stdout,):
        try:
            st.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(HERE / "stress_set.json"))
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--with-challenge", action="store_true", help="also include challenge_set.json")
    a = ap.parse_args()
    data = json.load(open(a.file, encoding="utf-8"))
    if a.with_challenge:
        for s in json.load(open(HERE / "challenge_set.json", encoding="utf-8")):
            s.setdefault("category", "challenge")
            data.append(s)
    has_model = sd.load()
    report("RULES ONLY", run(data, False), a.verbose)
    if has_model:
        report("RULES + MODEL (ensemble)", run(data, True), a.verbose)
    else:
        print("\n(model weights not found -> only rules-only results)")


if __name__ == "__main__":
    main()
