"""
eval_chunk_model.py — how accurate is the CHUNK model YOU trained?
==================================================================
Different from eval_accuracy.py:
  * eval_accuracy.py  -> measures the LIVE path (YAMNet + dial).
  * THIS file         -> measures danger_classifier_chunks.pkl, the model
                          you trained from your own labeled journeys.

It runs that model on audio it has NEVER seen: the stock clips in
sfx_training/ (car = SAFE, danger/scream/slap = DANGER).  Your model learned
from your room recordings, so this is a *generalization stress test* —
a rough score does NOT mean training failed, it means the model only knows
your data so far and more danger examples are needed.

Chunk-level: every 3-second chunk is one prediction.
File-level:  a clip counts as "caught" if the MAJORITY of its chunks predict
             danger (mirrors how a real journey needs sustained evidence).

Run (from the project root):
    python eval_chunk_model.py
"""

import os
import sys
import json
import pickle
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import librosa

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from train_model.audio_features import extract_features_from_array, features_to_vector

MODEL_PATH = BASE / "train_model" / "models" / "danger_classifier_chunks.pkl"
SFX_ROOT = BASE / "sfx_training"
CHUNK_SEC = 3
SR = 16000

# folder -> ground truth (same mapping as the rest of the project)
FOLDER_LABELS = {
    "car_sounds": 0,      # SAFE
    "danger_sounds": 1,   # DANGER
    "scream_sounds": 1,   # DANGER
    "slap_sounds": 1,     # DANGER
}
VALID_EXT = (".wav", ".mp3", ".flac", ".ogg", ".aiff", ".m4a")


def discover_files():
    files = []
    for folder, label in FOLDER_LABELS.items():
        d = SFX_ROOT / folder
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix.lower() in VALID_EXT:
                files.append((f, label, folder))
    return files


def chunk_vectors(audio):
    """Slice a waveform into 3s chunks and return [feature_vector,...]."""
    n = int(CHUNK_SEC * SR)
    vecs = []
    idx = 0
    while (idx + 1) * n <= len(audio):
        seg = audio[idx * n:(idx + 1) * n]
        idx += 1
        feats = extract_features_from_array(seg, SR)
        if feats is None:
            continue
        vecs.append(features_to_vector(feats))
    return vecs


def main():
    print("\n" + "=" * 72)
    print("  CHUNK-MODEL ACCURACY (your trained danger_classifier_chunks)")
    print("=" * 72)

    if not MODEL_PATH.exists():
        print(f"\nNo model yet at: {MODEL_PATH}")
        print("Train one first (in-app 'Risk Analysis Trainer' button,")
        print("   or:  python -m train_model.train_from_recordings )")
        return 1

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    print(f"\nLoaded model: {type(model).__name__}  <- {MODEL_PATH.name}")

    files = discover_files()
    if not files:
        print(f"\nNo clips found under {SFX_ROOT}")
        return 1

    # ── chunk-level accumulators (confusion matrix) ──
    TP = FP = TN = FN = 0     # truth=1 pred=1 | truth=0 pred=1 | truth=0 pred=0 | truth=1 pred=0
    rows = []
    for path, label, folder in files:
        try:
            audio, _ = librosa.load(str(path), sr=SR, mono=True, dtype=np.float32)
        except Exception:
            continue
        vecs = chunk_vectors(audio)
        if not vecs:
            continue
        X = np.vstack(vecs)
        preds = model.predict(X).astype(int)
        danger_frac = float(preds.mean())
        file_pred = 1 if danger_frac >= 0.5 else 0        # majority vote

        # chunk-level confusion (only meaningful vs file's own truth)
        for p in preds:
            if label == 1 and p == 1: TP += 1
            elif label == 0 and p == 1: FP += 1
            elif label == 0 and p == 0: TN += 1
            else: FN += 1

        rows.append({
            "file": path.name, "folder": folder,
            "truth": "DANGER" if label else "SAFE",
            "n_chunks": len(preds),
            "danger_chunk_frac": round(danger_frac, 2),
            "file_verdict": "DANGER" if file_pred else "SAFE",
            "correct": (file_pred == label),
        })

    total_chunks = TP + FP + TN + FN
    if total_chunks == 0:
        print("\nNo decodable chunks (features failed). Nothing to measure.")
        return 1

    acc = (TP + TN) / total_chunks
    danger_chunks = TP + FN
    safe_chunks = TN + FP
    recall = TP / danger_chunks if danger_chunks else float("nan")
    fp_rate = FP / safe_chunks if safe_chunks else float("nan")
    prec = TP / (TP + FP) if (TP + FP) else float("nan")

    # ── per-file table ──
    print("\nPer-file (chunk danger-fraction; majority = file verdict)")
    print("-" * 72)
    print(f"  {'truth':<7}{'verdict':<8}{'ok':<5}{'dgFr':<6}{'chunks':<7}file")
    print("-" * 72)
    for r in sorted(rows, key=lambda x: (x["truth"], x["folder"])):
        print(f"  {r['truth']:<7}{r['file_verdict']:<8}"
              f"{'Y' if r['correct'] else 'N':<5}{r['danger_chunk_frac']:<6}"
              f"{r['n_chunks']:<7}{r['file'][:34]}")

    # ── headline metrics ──
    files_ok = sum(1 for r in rows if r["correct"])
    danger_files = [r for r in rows if r["truth"] == "DANGER"]
    safe_files = [r for r in rows if r["truth"] == "SAFE"]
    dang_caught = sum(1 for r in danger_files if r["file_verdict"] == "DANGER")
    safe_clean = sum(1 for r in safe_files if r["file_verdict"] == "SAFE")

    print("\n" + "=" * 72)
    print("  WHAT THE MODEL YOU TRAINED ACTUALLY DOES (on unseen stock audio)")
    print("=" * 72)
    print(f"  Chunk-level accuracy        : {acc*100:.1f}%   ({total_chunks} chunks)")
    print(f"  Danger recall (caught)      : "
          f"{'n/a' if danger_chunks==0 else f'{recall*100:.0f}%'}   "
          f"({TP}/{danger_chunks} danger chunks)")
    print(f"  Danger precision            : "
          f"{'n/a' if (TP+FP)==0 else f'{prec*100:.0f}%'}   "
          f"({TP}/{TP+FP} predicted-danger were real)")
    print(f"  Safe false-alarm rate       : "
          f"{'n/a' if safe_chunks==0 else f'{fp_rate*100:.0f}%'}   "
          f"({FP}/{safe_chunks} safe chunks wrongly flagged)")
    print(f"  File-level: danger caught   : {dang_caught}/{len(danger_files)}")
    print(f"  File-level: safe stayed clean: {safe_clean}/{len(safe_files)}")
    print(f"  Overall files correct       : {files_ok}/{len(rows)}")

    print("\n  Confusion (chunks):  TP=%d FP=%d TN=%d FN=%d" % (TP, FP, TN, FN))
    print("\n  READ THIS: your model learned from YOUR room recordings and is")
    print("  being tested here on curated sound-effects — a different domain.")
    print("  A modest score is EXPECTED and is not a bug; it tells you how much")
    print("  more (and more varied) DANGER data you still need to collect.")

    out = BASE / "chunk_model_report.json"
    out.write_text(json.dumps({"metrics": {
        "chunk_accuracy": round(acc, 4), "danger_recall": None if danger_chunks == 0 else round(recall, 4),
        "danger_precision": None if (TP + FP) == 0 else round(prec, 4),
        "safe_false_alarm_rate": None if safe_chunks == 0 else round(fp_rate, 4),
        "confusion": {"TP": TP, "FP": FP, "TN": TN, "FN": FN},
    }, "files": rows}, indent=2), encoding="utf-8")
    print(f"\n  Detail saved to: {out.name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
