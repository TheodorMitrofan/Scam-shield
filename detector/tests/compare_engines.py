"""Head-to-head: scam_detector (this repo) vs scam_shield (Francesco, origin/model-train), same sets, same scoring.

Usage:  git worktree add ../fr-model origin/model-train
        python detector/tests/compare_engines.py <repo_root> ../fr-model
"""
import copy, csv, glob, json, os, re, sys, time, collections, importlib, io, contextlib
sys.stdout.reconfigure(encoding="utf-8")
ROOT, FR = sys.argv[1], sys.argv[2]
sys.path.insert(0, FR)
os.chdir(FR)  # his catalog uses relative paths

import scam_detector as sd
sd.load()
from scam_shield.pipeline import ScamShieldPipeline
FRP = ScamShieldPipeline()


def run_mine(s):
    r = sd.analyze(copy.deepcopy(s))
    return r["verdict"], r["scam_type"], r["first_alert"], r["red_flags"], r["warning"]["ro"]


def run_fr(s):
    r = FRP.analyze_scenario(copy.deepcopy(s))
    w = r.get("warning")
    if isinstance(w, dict):
        w = w.get("ro") or json.dumps(w, ensure_ascii=False)
    return r["verdict"], r["scam_type"], r["first_alert"], r["red_flags"], str(w)


# ---------------------------------------------------------------- collect test sets
def strip(s):
    return {k: v for k, v in s.items() if k in ("id", "channel", "sender", "messages")}

sets = collections.OrderedDict()
# official
exp = {r["id"]: r for r in csv.DictReader(open(f"{ROOT}/Scam_Shield_Public_Kit/validation_expected_results.csv", encoding="utf-8-sig"))}
sets["official validation (11)"] = [(json.load(open(f, encoding="utf-8")), {"verdict": exp[os.path.basename(f)[:-5]]["verdict"],
    "scam_type": exp[os.path.basename(f)[:-5]]["scam_type"],
    "first_alert": int(exp[os.path.basename(f)[:-5]]["first_alert"]) if exp[os.path.basename(f)[:-5]]["first_alert"] else None,
    "window": (3, 5) if os.path.basename(f).startswith("V11") else None})
    for f in sorted(glob.glob(f"{ROOT}/Scam_Shield_Public_Kit/validation_set/*.json"))]
# Giulio's sets
for name, fn in [("GIULIO stress (43)", "stress_set.json"), ("GIULIO blind (15)", "blind_set.json"), ("GIULIO challenge (15)", "challenge_set.json")]:
    data = json.load(open(f"{ROOT}/detector/tests/{fn}", encoding="utf-8"))
    sets[name] = [(strip(s), s["expected"]) for s in data]
# Francesco's inline stress test (capture test_cases by faking the pipeline)
import scam_shield.stress_test as fst
captured = []
class _Cap:
    def analyze_scenario(self, tc):
        captured.append(copy.deepcopy(tc))
        return {"verdict": "", "scam_type": "", "risk_score": 0, "red_flags": [], "warning": ""}
orig = fst.ScamShieldPipeline
fst.ScamShieldPipeline = lambda *a, **k: _Cap()
with contextlib.redirect_stdout(io.StringIO()):
    fst.run_stress_tests()
fst.ScamShieldPipeline = orig
sets[f"FRANCESCO stress_test.py ({len(captured)})"] = [(strip(tc), {"verdict": tc["expected_verdict"], "scam_type": tc["expected_type"],
                                                         "first_alert": None}) for tc in captured]
# Francesco's creative traps (folder + csv)
cexp = {r["id"]: r for r in csv.DictReader(open(f"{FR}/creative_traps_dataset/expected_results.csv", encoding="utf-8-sig"))}
rows = []
for f in sorted(glob.glob(f"{FR}/creative_traps_dataset/*.json")):
    s = json.load(open(f, encoding="utf-8"))
    e = cexp.get(s["id"])
    if e:
        rows.append((strip(s), {"verdict": e["expected_verdict"], "scam_type": e["expected_type"],
                                "first_alert": int(e["expected_alert"]) if e.get("expected_alert") else None}))
sets[f"FRANCESCO creative traps ({len(rows)})"] = rows
# Francesco's benchmark dataset (folder + csv)
bexp = {r["id"]: r for r in csv.DictReader(open(f"{FR}/benchmark_dataset/expected_results.csv", encoding="utf-8-sig"))}
rows = []
for f in sorted(glob.glob(f"{FR}/benchmark_dataset/*.json")):
    s = json.load(open(f, encoding="utf-8"))
    e = bexp.get(s["id"])
    if e:
        rows.append((strip(s), {"verdict": e["expected_verdict"], "scam_type": e["expected_type"], "first_alert": None}))
sets[f"FRANCESCO benchmark ({len(rows)})"] = rows


# ---------------------------------------------------------------- scoring (brief formula)
def score(e, got):
    v, t, fa = got[0], got[1], got[2]
    types = e["scam_type"] if isinstance(e["scam_type"], list) else [e["scam_type"]]
    pts, mx = (3 if v == e["verdict"] else 0) + (2 if t in types else 0), 5
    fa_ok = None
    if e["verdict"] != "SAFE" and e.get("first_alert"):
        mx += 2
        lo, hi = e.get("window") or (e["first_alert"], e["first_alert"])
        if fa is not None and lo <= fa <= hi:
            pts += 2; fa_ok = True
        elif fa is not None and fa == hi + 1:
            pts += 1; fa_ok = False
        else:
            fa_ok = False
    missed = e["verdict"] != "SAFE" and v == "SAFE"
    if missed:
        pts -= 3
    return pts, mx, v == e["verdict"], t in types, fa_ok, missed, e["verdict"] == "SAFE" and v != "SAFE"


LINK = re.compile(r"[a-z0-9\-]+(?:\[\.\]|\.)(?:com|net|info|xyz|top|online|site|co|biz|click|shop|io|ro)(?:/\S*)?", re.I)
PHONE = re.compile(r"(?:\+?\d[\d ]{8,}\d)")
OFFICIAL = {"bancadunarea.ro", "curierexpres.ro", "piatamea.ro", "megashop.ro", "anaf.ro"}
OFF_PH = {"0800100200", "0800300400", "0800500600", "0314039160"}


def warning_issues(s, w):
    issues = []
    texts = " ".join(str(m.get("text") or "") for m in s.get("messages") or [] if isinstance(m, dict))
    for l in LINK.findall(texts):
        dom = l.lower().split("/")[0]
        if dom not in OFFICIAL and l.lower() in (w or "").lower():
            issues.append("repeats link " + l)
    for p in PHONE.findall(texts):
        d = re.sub(r"\D", "", p)
        if d not in OFF_PH and len(d) >= 9 and d in re.sub(r"\D", "", w or ""):
            issues.append("repeats phone " + p)
    n_sent = len([x for x in re.split(r"(?<=[.!?])\s+", (w or "").strip()) if x])
    if n_sent > 3:
        issues.append(f"{n_sent} sentences")
    return issues


engines = [("GIULIO", run_mine), ("FRANCESCO", run_fr)]
summary = {}
fails = collections.defaultdict(list)
warn_bad = collections.Counter()
timing = collections.Counter()
for sname, rows in sets.items():
    for ename, fn in engines:
        agg = [0] * 7
        for s, e in rows:
            t0 = time.perf_counter()
            try:
                got = fn(s)
            except Exception as ex:
                got = ("CRASH", "CRASH", None, [], "")
                fails[(sname, ename)].append((s["id"], "CRASH " + repr(ex)[:80], e))
            timing[ename] += time.perf_counter() - t0
            timing[ename + "_n"] += 1
            p, m, vok, tok, faok, missed, falarm = score(e, got)
            agg[0] += p; agg[1] += m; agg[2] += vok; agg[3] += tok
            agg[4] += 1 if faok else 0; agg[5] += missed; agg[6] += falarm
            if not (vok and tok and faok is not False) and got[0] != "CRASH":
                fails[(sname, ename)].append((s["id"], f"{got[0]}/{got[1]}/fa={got[2]} {got[3]}", e))
            wi = warning_issues(s, got[4])
            if wi:
                warn_bad[ename] += 1
                fails[("WARN", ename)].append((s["id"], "; ".join(wi), got[4][:160]))
        summary[(sname, ename)] = (len(rows), agg, sum(1 for _, e in rows if e["verdict"] != "SAFE" and e.get("first_alert")))

print(f"{'test set':<34}{'engine':<11}{'n':>4}{'verdict':>9}{'type':>7}{'alert':>8}{'missed':>8}{'f.alarm':>9}{'points':>12}{'/30':>7}")
for sname in sets:
    for ename, _ in engines:
        n, a, nfa = summary[(sname, ename)]
        print(f"{sname:<34}{ename:<11}{n:>4}{a[2]:>9}{a[3]:>7}{(str(a[4]) + '/' + str(nfa)) if nfa else '-':>8}{a[5]:>8}{a[6]:>9}"
              f"{a[0]:>7}/{a[1]:<4}{30 * max(a[0], 0) / a[1]:>7.1f}")
    print()
for ename, _ in engines:
    print(f"{ename}: avg latency {1000 * timing[ename] / timing[ename + '_n']:.1f} ms/scenario; warnings with problems: {warn_bad[ename]}")

print("\n================ FAILURES ================")
for (sname, ename), lst in fails.items():
    print(f"\n--- {ename} on {sname}: {len(lst)}")
    for row in lst[:40]:
        print("   ", row[0], "|", row[1], "| exp", row[2] if not isinstance(row[2], dict) else
              f"{row[2]['verdict']}/{row[2]['scam_type']}/fa={row[2].get('first_alert')}")

# robustness
print("\n================ ROBUSTNESS ================")
garbage = [{}, {"messages": None}, {"messages": [None, 5, {"text": None}]}, {"id": 3, "sender": None, "messages": [{"n": 1, "text": "x"}]},
           {"id": "L", "channel": "sms", "sender": {}, "messages": [{"n": 1, "from": "sender", "text": "trimite-mi codul " * 2000}]}]
for ename, fn in engines:
    crashes = 0
    for g in garbage:
        try:
            fn(g)
        except Exception as ex:
            crashes += 1
            print(f"  {ename} crash on {str(g)[:60]}: {repr(ex)[:90]}")
    print(f"  {ename}: {crashes}/{len(garbage)} malformed inputs crashed")
