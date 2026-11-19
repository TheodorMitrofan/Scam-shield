"""„Nepotul e în Spania?” — check a place CLAIMED in a voice message against the aircraft heard behind it.

Synthetic demo only (like pipeline.demo): a ~100 s voice message from a fake grandson who says he is in
Madrid, recorded (simulated) near Bucharest-Băneasa with ONE propeller aircraft passing. Because the time of
a voice message is known, one fly-over is enough to answer a yes/no question per area:
  run_search(..., rec_start=<message time>, bbox=<claimed area>) → 0 candidates ⇒ the sound does NOT fit there.

Privacy by design: the result is only „se potrivește / nu se potrivește” per city — no coordinates of the
other person are returned. The technical detail is meant for the police (complaint annex), not for the user.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import unicodedata
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from .pipeline import FS, RECORDINGS_DIR, _spectrogram_png, adsb, audio, physics, C  # reuse the wrapper's setup

from afg.common import parse_time  # noqa: E402  (vendor path is set up by .pipeline)
from afg.dem import ElevationModel  # noqa: E402

CLIP_S = 100          # length of the voice message
FLYOVER_AT_S = 50.0   # the aircraft passes closest ~50 s into the message
CLOCK_TOL_S = 30.0    # how well we know the message time (WhatsApp shows minutes)
PLAYBACK_FS = 16000  # the original message people listen to
ANALYSIS_FS = 8000   # internal copy used only to detect the aircraft

# Places a scammer may claim. key → (label, lat, lon, ground elevation m). Coordinates = a GA airfield area,
# used only to simulate that area's air traffic at the same hour.
PLACES: dict[str, tuple[str, float, float, float]] = {
    "madrid": ("Madrid, Spania", 40.370, -3.785, 650.0),
    "barcelona": ("Barcelona, Spania", 41.520, 2.105, 110.0),
    "paris": ("Paris, Franța", 48.752, 2.106, 160.0),
    "milano": ("Milano, Italia", 45.540, 9.203, 140.0),
    "roma": ("Roma, Italia", 41.952, 12.499, 25.0),
    "londra": ("Londra, Marea Britanie", 51.571, -0.419, 50.0),
    "berlin": ("Berlin, Germania", 52.380, 13.520, 50.0),
    "viena": ("Viena, Austria", 48.110, 16.570, 180.0),
}
# Country names → the capital we test by default.
ALIASES = {"spania": "madrid", "franta": "paris", "italia": "roma", "anglia": "londra", "germania": "berlin",
           "austria": "viena", "marea britanie": "londra"}

# Where the (simulated) message was really recorded — own constant, independent of pipeline.SCENARIOS.
ACTUAL = {"place": "București, zona Aeroportului Băneasa", "lat": 44.503, "lon": 26.102, "ground": 90.0, "seed": 23}

TRANSCRIPT = [
    (3.0, "Mamă, sunt eu, Andrei. Mi s-a stricat telefonul, ăsta e numărul nou. Am făcut un accident aici, "
          "la Madrid, în Spania, și am nevoie de ajutor."),
    (40.0, "Poți să-mi faci tu un transfer de două mii de euro pentru avocat? Te rog să nu-i spui lui tata, "
           "se enervează. E urgent, până la ora cinci."),
]


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def claimed_place(text: str) -> str | None:
    """First city/country named in the message (diacritic-insensitive), e.g. „la Madrid” → 'madrid'."""
    t = _fold(text)
    hits = [(t.find(k), k) for k in PLACES if k in t] + [(t.find(a), ALIASES[a]) for a in ALIASES if a in t]
    return min(hits)[1] if hits else None


def _speech(work: str, start_s: float, text: str, n: int, fs: int, band_limited: bool) -> np.ndarray:
    """Synthetic Romanian voice (macOS `say`, voice Ioana) placed at start_s; silence if unavailable.

    band_limited=False → the ORIGINAL voice, used for the file people listen to.
    band_limited=True  → DEMO SIMPLIFICATION used only for the analysis copy: voice above 450 Hz so it does not
    cover the propeller tone the detector looks for (40–400 Hz). Real speech overlapping it is harder."""
    out = np.zeros(n)
    if not (shutil.which("say") and shutil.which("ffmpeg")):
        return out
    aiff = os.path.join(work, f"s{start_s:.0f}.aiff")
    wav = os.path.join(work, f"s{start_s:.0f}_{fs}_{'band' if band_limited else 'orig'}.wav")
    try:
        if not os.path.exists(aiff):
            subprocess.run(["say", "-v", "Ioana", "-o", aiff, text], check=True, capture_output=True, timeout=60)
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", aiff, "-ac", "1", "-ar", str(fs)]
        if band_limited:
            cmd += ["-af", "highpass=f=450,highpass=f=450"]
        subprocess.run(cmd + [wav], check=True, capture_output=True, timeout=60)
    except Exception:
        return out
    sr, s = wavfile.read(wav)
    s = s.astype(float) / (np.abs(s).max() or 1.0)
    a = int(start_s * fs)
    m = min(len(s), n - a)
    if m > 0:
        out[a:a + m] = 0.55 * s[:m]
    return out


def _tracks(work: str, tdir: str, truth: dict, name: str):
    from afg.tracks import Flights, Resampled
    types = adsb.load_type_table(allow_download=False)
    day = [parse_time(s) for s in truth["day_window"]]
    acc = adsb.ingest_readsb([tdir], day[0], day[1], None, types=types)
    cols, flights = adsb.finalize(acc)
    path = os.path.join(work, f"{name}.npz")
    adsb.save_tracks(path, cols, flights, {})
    fl = Flights(path)
    return fl, Resampled(fl, dt=1.0)


def verify_claim(claimed_key: str = "madrid") -> dict:
    """Simulate the voice message, detect the fly-over in the MIXED audio, then test the claimed area and the
    real area with the known message time. Returns a city-level verdict only."""
    from afg.search import run_search
    from afg.simulate import simulate

    label, clat, clon, cground = PLACES[claimed_key]
    t_start = time.time()
    with tempfile.TemporaryDirectory(prefix="afg_claim_") as work:
        # 1) the message: recorded near Băneasa, one propeller aircraft passing at ~50 s
        truth, wav, tdir = simulate(os.path.join(work, "real"), lat0=ACTUAL["lat"], lon0=ACTUAL["lon"],
                                    ground=ACTUAL["ground"], seed=ACTUAL["seed"], t1_rec=FLYOVER_AT_S)
        x4, fs4, _ = audio.load_audio(wav, fs=FS)
        clip = x4[: CLIP_S * fs4]

        # (a) ORIGINAL voice message — what the user hears when pressing play
        plane_o = resample_poly(clip, PLAYBACK_FS // FS, 1)
        original = plane_o + sum(_speech(work, t0, txt, len(plane_o), PLAYBACK_FS, False) for t0, txt in TRANSCRIPT)
        original = 0.9 * original / (np.abs(original).max() or 1.0)
        RECORDINGS_DIR.mkdir(exist_ok=True)
        wavfile.write(RECORDINGS_DIR / "claim.wav", PLAYBACK_FS, (original * 32767).astype(np.int16))

        # (b) analysis copy (never served): same message with the voice band-limited, see _speech()
        plane_a = resample_poly(clip, ANALYSIS_FS // FS, 1)
        mix = plane_a + sum(_speech(work, t0, txt, len(plane_a), ANALYSIS_FS, True) for t0, txt in TRANSCRIPT)
        mix = 0.9 * mix / (np.abs(mix).max() or 1.0)
        x = resample_poly(mix, 1, ANALYSIS_FS // FS)
        spec = audio.compute_spectrogram(x, FS, 1.0, 0.2, 20, 600, 120)
        # Speech can split one fly-over into several boxes: try the longest descending ones first and keep
        # the first that fits the physics of a single aircraft passing (same rule a real upload would use).
        boxes = sorted((e for e in audio.detect_events(spec, 40, 400, 1) if e["trend"] == "descending"),
                       key=lambda e: -(e["t1"] - e["t0"]))
        corr = np.sqrt(1.0 / 0.2)
        b = tt = f = fit = None
        for cand_box in boxes:
            try:
                tt, f, _ = audio.trace_curve(spec, cand_box["t0"], cand_box["t1"], cand_box["fmin"], cand_box["fmax"], n_harm=3)
                fit = physics.fit_linear(tt, f, c=C, corr_factor=corr)
                # plausibility gate for a small propeller aircraft — a bad fit would explode the search area
                if not (80 / 3.6 <= fit["v"] <= 450 / 3.6 and 0 < fit["d"] <= 5000):
                    continue
                b = cand_box
                break
            except ValueError:
                continue
        if b is None:
            return {"ok": False, "reason": "Nu se aude niciun avion în mesaj, deci nu putem verifica locul."}
        cons = physics.search_constraints(fit, alt=physics.fit_split(tt, f, fit, c=C, corr_factor=corr))
        cons["name"] = "e1"
        if cons["d_max"] > 8000:  # still too vague to search safely
            return {"ok": False, "reason": "Avionul se aude prea slab ca să putem verifica locul."}
        rec_start = float(truth["rec_start_unix"])

        def check(tdir_x: str, truth_x: dict, name: str) -> dict:
            fl, R = _tracks(work, tdir_x, truth_x, name)
            dem = ElevationModel(constant=truth_x["observer"]["ground_elev_m"])
            cand, st = run_search(R, fl, [cons], dem, tuple(truth_x["bbox"]), 200.0, C,
                                  rec_start=rec_start, rec_start_tol=CLOCK_TOL_S, rec_duration=CLIP_S)
            best_score, consistent = None, False
            if len(cand):
                from afg.scoring import score_candidates, trace_check
                ranked, _, _ = score_candidates(cand, R, spec, [cons], dem, C, traces=[(tt, f)],
                                                clock=(rec_start, CLOCK_TOL_S))
                ranked = trace_check(R, ranked, [cons], [(tt, f)], [fit], C)
                ok = [r for r in ranked if (r.get("trace_check") or {}).get("consistent")]
                consistent = bool(ok)
                best_score = float(max((r["total"] for r in (ok or ranked)), default=0.0))
            return {"match": bool(len(cand)) and consistent, "candidates": int(len(cand)), "curve_consistent": consistent,
                    "best_score": best_score, "flights_in_area": int(st.get("flights_total", 0)),
                    "aircraft_that_fit": int(st.get("flight_pairs", 0))}

        actual = check(tdir, truth, "actual")
        # 3) the claimed area's air traffic on the same day (simulated), searched at the SAME minute
        truth_c, _, tdir_c = simulate(os.path.join(work, "claimed"), lat0=clat, lon0=clon, ground=cground,
                                      seed=ACTUAL["seed"] + 1)
        claimed = check(tdir_c, truth_c, "claimed")

    return {
        "ok": True,
        "simulated": True,
        "transcript": " ".join(t for _, t in TRANSCRIPT),
        "transcript_parts": [t for _, t in TRANSCRIPT],
        "message_time_utc": truth["rec_start_utc"],
        "duration_s": CLIP_S,
        "claimed": {"key": claimed_key, "label": label, **claimed},
        "actual": {"label": ACTUAL["place"], **actual},
        "event": {"t_cpa_s": float(fit["t_cpa_rx"]), "speed_kmh": float(fit["v"] * 3.6), "distance_m": float(fit["d"])},
        "runtime_s": time.time() - t_start,
        "spectrogram": _spectrogram_png(spec, [b], [(tt, f)], title="Mesaj vocal: vocea + un avion care trece"),
    }
