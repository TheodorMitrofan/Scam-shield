"""Thin wrapper around the vendored `afg` pipeline (audio-flyover-geolocation, MIT, see vendor/afg/LICENSE).

Two features only, both privacy-safe:
  * audit(wav)  — does a recording the user made THEMSELVES leak where it was recorded (aircraft fly-overs)?
  * demo(seed)  — the full localisation chain on a SYNTHETIC recording, to explain the technique.
We deliberately do NOT expose "locate the speaker of an uploaded call": the upstream project forbids
locating private individuals from private calls, and it would work on anyone's audio.
"""

from __future__ import annotations

import base64
import io
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from afg import adsb, audio, physics  # noqa: E402
from afg.common import parse_time  # noqa: E402
from afg.dem import ElevationModel  # noqa: E402
from afg.geo import haversine_m  # noqa: E402

FS = 4000  # the pipeline works on 4 kHz mono
C = 343.0


def _png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _spectrogram_png(spec, boxes=(), traces=(), title="", rejected=()) -> str:
    t, f, W = spec["t"], spec["f"], spec["W"]
    sel = (f >= 20) & (f <= 500)
    img = W[sel]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    vm = max(6.0, float(np.percentile(img, 99.7))) if img.size else 6.0
    ax.imshow(img, origin="lower", aspect="auto", cmap="magma", vmin=0, vmax=vm,
              extent=[t[0], t[-1], f[sel][0], f[sel][-1]], interpolation="nearest")
    for i, b in enumerate(boxes):
        ax.add_patch(plt.Rectangle((b["t0"], b["fmin"]), b["t1"] - b["t0"], b["fmax"] - b["fmin"],
                                   fill=False, ec="#38bdf8", lw=1.6))
        ax.text(b["t0"], b["fmax"] + 6, f"avion {i + 1}", color="#38bdf8", fontsize=9)
    for b in rejected:
        ax.add_patch(plt.Rectangle((b["t0"], b["fmin"]), b["t1"] - b["t0"], b["fmax"] - b["fmin"],
                                   fill=False, ec="#9ca3af", lw=1.0, ls="--"))
        ax.text(b["t0"], b["fmin"] - 14, "nu e avion", color="#9ca3af", fontsize=8)
    for tt, ff in traces:
        ax.plot(tt, ff, ".", color="#4ade80", ms=2.5)
    ax.set_xlabel("timp (s)")
    ax.set_ylabel("frecvență (Hz)")
    if title:
        ax.set_title(title)
    return _png(fig)


# ----------------------------------------------------------------------------- audit (own recording)

def _confirm(spec, e) -> dict | None:
    """Physics check: trace the candidate's ridge and fit the Doppler model. Real fly-overs give a
    plausible pass (props: < 150 m/s, within ~15 km, well constrained); speech, music and room noise
    either fail the fit or give impossible values. Returns the fit summary, or None if not an aircraft."""
    try:
        t, f, _ = audio.trace_curve(spec, e["t0"], e["t1"], e["fmin"], e["fmax"], n_harm=3)
        if len(t) < 20:
            return None
        fit = physics.fit_linear(t, f, c=C, corr_factor=np.sqrt(1.0 / 0.2))
    except (ValueError, RuntimeError, np.linalg.LinAlgError):
        return None
    if physics.plausibility(fit):
        return None
    return {"v_ms": float(fit["v"]), "d_m": float(fit["d"]), "f0_hz": float(fit["f0"]), "trace": (t, f)}


def audit(wav_path: str) -> dict:
    """Privacy self-check of the user's own recording (based on `afg_cli.py audit`).

    Stricter than upstream on purpose: the raw detector flags speech in short clips (status 'limited')
    as fly-overs, and a false alarm on an ordinary voice message teaches people to ignore warnings.
    So every candidate must also pass the Doppler physics check before it counts as an aircraft."""
    x, fs, _ = audio.load_audio(wav_path, fs=FS)
    dur = len(x) / fs
    if dur < 1.0:
        return {"duration_s": dur, "risk": "undetermined", "flyovers": 0, "events": [], "rejected": 0,
                "status": "insufficient", "limited": True, "reasons": ["Înregistrarea e mai scurtă de o secundă."],
                "spectrogram": None}
    spec = audio.compute_spectrogram(x, fs, 1.0, 0.2, 20, 600, 120)
    ev, info = audio.detect_events(spec, 40, 400, 1, 0.8, 12.0, return_info=True)

    confirmed, rejected = [], []
    for e in ev:
        if e["trend"] != "descending":
            rejected.append(e)
            continue
        fit = _confirm(spec, e)
        (confirmed if fit else rejected).append(dict(e, fit=fit) if fit else e)

    n = len(confirmed)
    status = info["status"]
    if n >= 2:
        risk = "high"
    elif n == 1:
        risk = "medium"
    elif status == "insufficient":
        risk = "undetermined"
    else:
        risk = "low"

    events = [{"t0": float(e["t0"]), "t1": float(e["t1"]), "fmin": float(e["fmin"]), "fmax": float(e["fmax"]),
               "speed_kmh": e["fit"]["v_ms"] * 3.6, "distance_m": e["fit"]["d_m"]} for e in confirmed]
    return {
        "duration_s": dur,
        "risk": risk,
        "flyovers": n,
        "events": events,
        "rejected": len(rejected),
        "status": status,
        "limited": status != "ok",
        "reasons": [str(r) for r in info.get("reasons", [])],
        "spectrogram": _spectrogram_png(
            spec, confirmed, [e["fit"]["trace"] for e in confirmed], rejected=rejected,
            title="Căutăm curbe care coboară (avioane care trec)"),
    }


# ----------------------------------------------------------------------------- demo (synthetic)

def demo(seed: int = 23) -> dict:
    """Synthetic blind test, two fly-overs with unknown clock (the method's main mode)."""
    from afg.scoring import heatmap, rank_consistent, score_candidates, trace_check
    from afg.search import run_search
    from afg.simulate import simulate
    from afg.tracks import Flights, Resampled

    t_start = time.time()
    with tempfile.TemporaryDirectory(prefix="afg_demo_") as work:
        truth, wav, tdir = simulate(work, seed=seed)
        x, fs, _ = audio.load_audio(wav, fs=FS)
        spec = audio.compute_spectrogram(x, fs, 1.0, 0.2, 20, 600, 120)
        boxes = sorted(audio.detect_events(spec, 40, 400, 1), key=lambda e: -e["score_z"])[:2]
        boxes.sort(key=lambda e: e["t0"])
        if len(boxes) < 2:
            return {"ok": False, "reason": "Nu am găsit două treceri de avion în înregistrarea simulată."}

        events, traces, fits = [], [], []
        corr = np.sqrt(1.0 / 0.2)
        for k, b in enumerate(boxes):
            t, f, _ = audio.trace_curve(spec, b["t0"], b["t1"], b["fmin"], b["fmax"], n_harm=3)
            fit = physics.fit_linear(t, f, c=C, corr_factor=corr)
            cons = physics.search_constraints(fit, alt=physics.fit_split(t, f, fit, c=C, corr_factor=corr))
            cons["half_span_s"] = float(max(fit["t_cpa_rx"] - t.min(), t.max() - fit["t_cpa_rx"]))
            cons["name"] = f"e{k + 1}"
            events.append(cons)
            traces.append((t, f))
            fits.append(fit)

        # Offline on purpose: built-in aircraft type table, no download.
        types = adsb.load_type_table(allow_download=False)
        day = [parse_time(s) for s in truth["day_window"]]
        acc = adsb.ingest_readsb([tdir], day[0], day[1], None, types=types)
        cols, flights = adsb.finalize(acc)
        tracks = os.path.join(work, "tracks.npz")
        adsb.save_tracks(tracks, cols, flights, {})
        fl = Flights(tracks)
        R = Resampled(fl, dt=1.0)
        dem = ElevationModel(constant=truth["observer"]["ground_elev_m"])
        bbox = tuple(truth["bbox"])

        cand, stats = run_search(R, fl, events, dem, bbox, 200.0, C, rec_duration=truth["rec_duration_s"])
        ranked = []
        if cand.size:
            ranked, _, _ = score_candidates(cand, R, spec, events, dem, C)
            ranked = rank_consistent(trace_check(R, ranked, events, traces, fits, C), 2)
        if not ranked:
            return {"ok": False, "reason": "Căutarea nu a găsit niciun loc potrivit."}
        best = ranked[0]

        la, lo, tot, _, E, N = heatmap(R, spec, events, dem, best, C, radius_m=600.0, step_m=40.0)
        pk = np.nanmax(tot)
        kp = np.unravel_index(np.nanargmax(tot), tot.shape)
        region = float(np.hypot(E[tot >= 0.9 * pk] - E[kp], N[tot >= 0.9 * pk] - N[kp]).max())

        ob = truth["observer"]
        err = float(haversine_m(best["lat"], best["lon"], ob["lat"], ob["lon"]))
        matched = [int(best["fid1"]), int(best["fid2"])]

        fig, ax = plt.subplots(figsize=(5.2, 4.6))
        im = ax.pcolormesh(E, N, tot / pk, shading="auto", cmap="inferno")
        ax.set_aspect("equal")
        ax.set_xlabel("est (m)")
        ax.set_ylabel("nord (m)")
        ax.set_title("Cât de bine se potrivește fiecare loc")
        fig.colorbar(im, ax=ax, shrink=0.8)
        heat_png = _png(fig)

        # Map data: every flight's track (downsampled) inside the bbox; the two matched ones flagged.
        flights_out = []
        for fid in range(fl.nflights):
            m = fl.fid == fid
            if not m.any():
                continue
            order = np.argsort(fl.t[m])
            lat, lon = fl.lat[m][order], fl.lon[m][order]
            step = max(1, lat.size // 80)
            flights_out.append({
                "id": str(fl.hex[fid]),
                "type": str(fl.type[fid] or ""),
                "prop": "J" not in str(fl.desc[fid] or ""),
                "matched": fid in matched,
                "points": [[float(a), float(b)] for a, b in zip(lat[::step], lon[::step])],
            })

        return {
            "ok": True,
            "seed": seed,
            "runtime_s": time.time() - t_start,
            "recording_s": float(truth["rec_duration_s"]),
            "truth": {"lat": float(ob["lat"]), "lon": float(ob["lon"])},
            "estimate": {"lat": float(best["lat"]), "lon": float(best["lon"])},
            "error_m": err,
            "region_radius_m": region,
            "bbox": [float(v) for v in bbox],
            "candidates_scored": len(ranked),
            "events": [{"v_ms": float(fi["v"]), "d_m": float(fi["d"]), "t_cpa_s": float(fi["t_cpa_rx"]),
                        "f0_hz": float(fi["f0"])} for fi in fits],
            "matched_flights": [{"id": str(fl.hex[i]), "type": str(fl.type[i] or "")} for i in matched],
            "flights": flights_out,
            "spectrogram": _spectrogram_png(spec, boxes, traces, title="Înregistrare simulată: două avioane trec pe deasupra"),
            "heatmap": heat_png,
        }
