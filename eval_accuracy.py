"""
eval_accuracy.py — REAL-AUDIO evaluation of the danger pipeline (Step #1)
==========================================================================
Why this exists
---------------
`test_scenarios.py` types feature numbers BY HAND and feeds them straight into
the scorer, so it only proves the dial *arithmetic*.  It cannot see the thing
that actually breaks: real audio being mislabelled (car noise → "danger").

This harness runs real files from `sfx_training/` through the SAME code path the
live app uses — librosa decode → yamnet_engine.classify_audio → DangerScorer —
and measures behaviour as a SEQUENCE, because your system is temporal (it climbs
on matching patterns and decays after events).  It reports, per class:

  SAFE (car_sounds)
    • single-chunk false-alarm rate  (YAMNet/fusion said DANGER on a safe clip)
    • whether the DIAL ever climbed to HIGH RISK / CRITICAL on pure car audio
  DANGER (danger/scream/slap)
    • detection rate  (did the dial reach ELEVATED+)
    • median chunks-to-first-raise  (a latency proxy: 3 s chunks → ~×3 s)
    • decay check  (did the dial fall back after the sound stopped)

It deliberately uses word_severity=0 (no browser transcript offline) so it
isolates the AUDIO-driven false alarms — which is exactly the failure you
described.  A live journey with speech would add the word signal on top.

Run (from the project root):
    python eval_accuracy.py
"""

import os
import sys
import io
import json
import wave
import math
import contextlib
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import numpy as np
import librosa

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yamnet_engine import classify_audio, preload_models
from scoring_engine import DangerScorer

SFX_ROOT = Path(__file__).parent / "sfx_training"
CHUNK_SEC = 3
SR = 16000

# folder -> ground-truth label (mirrors train_classifier.FOLDER_LABELS)
FOLDER_LABELS = {
    "car_sounds": "SAFE",
    "danger_sounds": "DANGER",
    "scream_sounds": "DANGER",
    "slap_sounds": "DANGER",
}
# dial_level thresholds (scoring_engine.DIAL_LEVELS order:
# 0 NORMAL, 1 CONCERNING, 2 ELEVATED, 3 HIGH RISK, 4 CRITICAL)
ALARM_LEVEL = 3      # >= this counts as a false alarm on safe audio
DETECT_LEVEL = 2     # >= this counts as "caught" on danger audio


def discover_files():
    files = []
    for folder, label in FOLDER_LABELS.items():
        d = SFX_ROOT / folder
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix.lower() in (".wav", ".mp3", ".flac", ".ogg", ".aiff", ".m4a"):
                files.append((f, label, folder))
    return files


def load_audio(path):
    """Return float32 mono @16k, or None if undecodable."""
    try:
        a, _ = librosa.load(str(path), sr=SR, mono=True, dtype=np.float32)
        return a
    except Exception as e:
        return None


def chunks(audio):
    n = int(CHUNK_SEC * SR)
    idx = 0
    while (idx + 1) * n <= len(audio):
        yield audio[idx * n:(idx + 1) * n]
        idx += 1


def evaluate_file(path, scorer):
    """Run one file through the live path. Returns a per-file result dict."""
    audio = load_audio(path)
    if audio is None or len(audio) < CHUNK_SEC * SR:
        return None  # undecodable / too short

    per_chunk = []
    for chunk in chunks(audio):
        energy = float(np.mean(chunk ** 2))
        peak = float(np.max(np.abs(chunk))) if len(chunk) else 0.0
        # Silence yamnet's chatty per-chunk [YAMNet] Top 5 prints
        with contextlib.redirect_stdout(io.StringIO()):
            res = classify_audio(chunk, SR)
            dial = scorer.process_chunk(
                word_severity=0,
                energy=energy,
                peak=peak,
                yamnet_top_name=res["sound_name"],
            )
        per_chunk.append({
            "chunk_status": res["status"],              # single-chunk verdict
            "sound_name": res["sound_name"],
            "confidence": round(res["confidence"], 3),
            "dial_level": dial["dial_level"],
            "dial_label": dial["dial_label"],
            "dial_score": round(dial["accumulated_score"], 2),
        })
    return per_chunk


def summarize(per_chunk):
    max_level = max((c["dial_level"] for c in per_chunk), default=0)
    danger_chunks = sum(1 for c in per_chunk if c["chunk_status"] == "DANGER")
    # first chunk index where dial reached DETECT_LEVEL
    first_detect = next((i for i, c in enumerate(per_chunk)
                         if c["dial_level"] >= DETECT_LEVEL), None)
    return {
        "n_chunks": len(per_chunk),
        "danger_chunk_rate": danger_chunks / max(1, len(per_chunk)),
        "max_dial_level": max_level,
        "max_dial_label": per_chunk[max(range(len(per_chunk)),
                              key=lambda i: per_chunk[i]["dial_level"])]["dial_label"]
                          if per_chunk else "NORMAL",
        "first_detect_chunk": first_detect,
        "final_dial_label": per_chunk[-1]["dial_label"] if per_chunk else "NORMAL",
        "top_sound": per_chunk[0]["sound_name"] if per_chunk else "",
    }


def main():
    print("\n" + "=" * 74)
    print("  AUDIO SAFETY AI — REAL-AUDIO ACCURACY HARNESS (Step #1)")
    print("=" * 74)

    # ── Integrity guard: refuse to run blind ──────────────────────
    print("\n[1/4] Loading the live model exactly as server.py does...")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            preload_models()
            probe = classify_audio(
                (0.1 * np.sin(2 * np.pi * 440 * np.arange(SR) / SR)).astype(np.float32),
                SR)
        assert "status" in probe and probe["sound_name"] != "Classification error"
        print("      ✓ YAMNet loaded and classifying (pipeline is not blind).")
    except Exception as e:
        print(f"      ✗ PIPELINE NOT FUNCTIONAL: {e}")
        print("        Fix model loading before trusting ANY accuracy number.")
        return 2

    files = discover_files()
    if not files:
        print(f"\nNo audio found under {SFX_ROOT}")
        return 1
    print(f"\n[2/4] Found {len(files)} candidate clips. Running each through"
          "\n      classify_audio() + DangerScorer (word_severity=0)...")

    results = []
    skipped = []
    for path, label, folder in files:
        scorer = DangerScorer()  # fresh dial per file (independent journeys)
        with contextlib.redirect_stdout(io.StringIO()):
            per_chunk = evaluate_file(path, scorer)
        if per_chunk is None:
            skipped.append((path.name, folder))
            continue
        s = summarize(per_chunk)
        s.update({"file": path.name, "folder": folder, "label": label})
        results.append(s)

    # ── Report ────────────────────────────────────────────────────
    print("\n[3/4] Per-file results")
    print("-" * 74)
    print(f"  {'label':<7}{'chunks':<7}{'YAMnetDanger%':<16}{'maxDial':<12}{'firstDetect':<13}{'final'}")
    print("-" * 74)
    for r in results:
        fd = r["first_detect_chunk"]
        fd_str = f"#{fd}" if fd is not None else "never"
        print(f"  {r['label']:<7}{r['n_chunks']:<7}"
              f"{r['danger_chunk_rate']*100:<16.0f}{r['max_dial_label']:<12}"
              f"{fd_str:<13}{r['final_dial_label']}")

    safe = [r for r in results if r["label"] == "SAFE"]
    dang = [r for r in results if r["label"] == "DANGER"]

    # ── Metrics that map to YOUR described behaviour ──────────────
    print("\n[4/4] What this says about the behaviour you asked about")
    print("=" * 74)

    if safe:
        fa_files = [r for r in safe if r["max_dial_level"] >= ALARM_LEVEL]
        fa_chunk_rate = sum(r["danger_chunk_rate"] for r in safe) / len(safe)
        print(f"  CAR-SOUND FALSE ALARMS (should be ~0):")
        print(f"    - avg single-chunk DANGER rate on car audio : {fa_chunk_rate*100:.1f}%")
        print(f"    - car files whose DIAL hit HIGH RISK+       : {len(fa_files)}/{len(safe)}")
        for r in fa_files:
            print(f"        ! {r['file'][:48]:<48} max={r['max_dial_label']}")
    else:
        print("  No SAFE/car clips were decodable — cannot measure false-alarm rate.")

    if dang:
        caught = [r for r in dang if r["max_dial_level"] >= DETECT_LEVEL]
        lats = [r["first_detect_chunk"] for r in dang if r["first_detect_chunk"] is not None]
        med_lat = (sorted(lats)[len(lats)//2] if lats else None)
        print(f"\n  DANGER DETECTION (should climb on real danger):")
        print(f"    - danger files that reached ELEVATED+        : {len(caught)}/{len(dang)}")
        print(f"    - median chunks to first raise               : "
              f"{('#'+str(med_lat)+' (~'+str(med_lat*CHUNK_SEC)+'s)') if med_lat is not None else 'n/a'}")
        missed = [r for r in dang if r["max_dial_level"] < DETECT_LEVEL]
        for r in missed:
            print(f"        · missed/low: {r['file'][:44]:<44} max={r['max_dial_label']}")
    else:
        print("  No DANGER clips were decodable — cannot measure detection.")

    if skipped:
        print(f"\n  Skipped (undecodable by librosa/libsndfile): {len(skipped)}")
        for name, folder in skipped:
            print(f"        - {folder}/{name[:50]}")

    print("\n  NOTE: word_severity=0 here — this isolates the AUDIO false-positive"
          "\n        problem. Live journeys add the transcript/keyword signal on top."
          "\n        Re-run this after every tuning change and compare. That is what"
          "\n        turns 'I think it's accurate' into a number you can track.\n")

    # machine-readable dump for tracking across runs
    out = Path(__file__).parent / "eval_report.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"  Full per-file data saved to: {out.name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
