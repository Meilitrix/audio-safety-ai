"""
train_model/train_from_recordings.py
====================================
Train a CHUNK-level danger classifier from your human-labeled saved journeys.

This is the payoff of the "record -> label -> train" loop in the app:
  1. You monitor a journey, stop, and it saves to saved_journeys/<id>.wav
  2. In the archive you click "Mark all safe"  -> whole journey = safe
     or "Review chunks" + Save labels          -> per 3s chunk danger/safe/skip
  3. This script reads those sidecar labels (saved_journeys/<id>.label.json),
     slices each journey into 3-second chunks, extracts the SAME features the
     live predictor uses (train_model/audio_features), and fits a second model.

It writes  models/danger_classifier_chunks.pkl  -- a SEPARATE file.
The existing whole-file model (danger_classifier_latest.pkl) is never touched,
so nothing in the live app breaks.  ("runs alongside")

Run:  python -m train_model.train_from_recordings
"""

import os
import sys
import json
import pickle
from pathlib import Path
from datetime import datetime

import numpy as np
import librosa

BASE_DIR = Path(__file__).resolve().parent.parent   # project root
PACKAGE_DIR = Path(__file__).resolve().parent       # train_model/
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from train_model.audio_features import extract_features_from_array, features_to_vector

JOURNEY_DIR = BASE_DIR / "saved_journeys"
MODELS_DIR = PACKAGE_DIR / "models"
MODEL_OUT = MODELS_DIR / "danger_classifier_chunks.pkl"
META_OUT = MODELS_DIR / "model_chunks_metadata.json"

SR = 16000
CHUNK_SEC = 3


def load_labeled_chunks():
    """
    Walk saved_journeys/*.wav, read each sidecar <name>.label.json, slice the
    WAV into 3-second chunks and turn every chunk into a labelled sample.

    Rules (must match the app's labelling semantics):
      - journey label "safe"    -> every chunk is a SAFE sample
      - journey label "danger"  -> a chunk marked "danger" = DANGER,
                                   "ignore"/"skip" = dropped,
                                   anything NOT marked = SAFE
      - journeys with no label are skipped (still unreviewed)

    Returns (X, y, report) where y is 0=SAFE / 1=DANGER.
    """
    step = int(SR * CHUNK_SEC)
    X, y = [], []
    per_journey = {}

    if not JOURNEY_DIR.exists():
        return np.array([]), np.array([]), per_journey

    for wav in sorted(JOURNEY_DIR.glob("*.wav")):
        label_file = wav.with_name(wav.stem + ".label.json")
        if not label_file.exists():
            continue
        try:
            lab = json.loads(label_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [skip] {wav.name}: bad label file ({e})")
            continue

        jlabel = lab.get("label")
        if not jlabel:
            continue

        chunk_map = {}
        for c in lab.get("chunks", []):
            try:
                chunk_map[int(c["index"])] = c.get("label", "safe")
            except (KeyError, TypeError, ValueError):
                continue

        try:
            audio, sr = librosa.load(str(wav), sr=SR, mono=True)
        except Exception as e:
            print(f"  [skip] {wav.name}: decode failed ({e})")
            continue

        counts = {"SAFE": 0, "DANGER": 0, "SKIP": 0}
        n = int(np.ceil(len(audio) / step))
        for i in range(n):
            seg = audio[i * step:(i + 1) * step]
            if len(seg) < step // 3:
                continue
            feats = extract_features_from_array(seg, sr)
            if feats is None:
                continue
            vec = features_to_vector(feats)

            if jlabel == "safe":
                target = 0
            else:  # "danger" journey -> per-chunk decision
                cl = chunk_map.get(i, "safe")
                if cl in ("ignore", "skip"):
                    counts["SKIP"] += 1
                    continue
                target = 1 if cl == "danger" else 0

            X.append(vec)
            y.append(target)
            counts["DANGER" if target == 1 else "SAFE"] += 1

        per_journey[wav.name] = counts

    return np.asarray(X, dtype=float), np.asarray(y, dtype=int), per_journey


def build_candidates():
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.svm import SVC
    from sklearn.neighbors import KNeighborsClassifier

    # class_weight="balanced" matters a lot here: your DANGER chunks are few
    # and SAFE chunks are plentiful, so we stop the model ignoring danger.
    return {
        "Random Forest": Pipeline([
            ("sc", StandardScaler()),
            ("m", RandomForestClassifier(n_estimators=200, random_state=42,
                                         class_weight="balanced")),
        ]),
        "SVM (RBF)": Pipeline([
            ("sc", StandardScaler()),
            ("m", SVC(kernel="rbf", probability=True, class_weight="balanced",
                      random_state=42)),
        ]),
        "KNN": Pipeline([
            ("sc", StandardScaler()),
            ("m", KNeighborsClassifier(n_neighbors=5)),
        ]),
    }


def run_training():
    """
    Programmatic entry used by BOTH the CLI (main) and the in-app
    "Risk Analysis Trainer" button (server POST /train).  Reads every labeled
    journey, fits a chunk-level classifier, and returns a JSON-safe result
    dict.  It does NOT raise for "not enough data" -- it reports via
    result["message"] so the button can show it.
    """
    MODELS_DIR.mkdir(exist_ok=True)
    X, y, per = load_labeled_chunks()
    n_safe = int((y == 0).sum()) if len(y) else 0
    n_danger = int((y == 1).sum()) if len(y) else 0

    result = {
        "ok": False,
        "n_journeys": len(per),
        "n_safe": n_safe,
        "n_danger": n_danger,
        "per_journey": per,
        "cv_report": None,
        "model": None,
        "message": "",
    }

    if len(X) == 0:
        result["message"] = ("No labeled journeys yet. Record + label some "
                             "('Mark all safe' or 'Review chunks'), then train.")
        return result

    if n_danger < 2 or n_safe < 2:
        result["message"] = (f"Not enough of both classes yet: SAFE={n_safe}, "
                             f"DANGER={n_danger}. Need >=2 of each. Label more "
                             f"journeys -- especially ones with real danger moments.")
        return result

    from sklearn.model_selection import cross_val_score, StratifiedKFold
    cv = StratifiedKFold(n_splits=min(3, n_danger, n_safe), shuffle=True, random_state=42)
    best, best_name, best_f1 = None, None, -1.0
    cv_report = {}
    for nm, pipe in build_candidates().items():
        try:
            f1 = float(cross_val_score(pipe, X, y, cv=cv, scoring="f1_macro").mean())
        except Exception:
            f1 = float("nan")
        cv_report[nm] = None if (f1 != f1) else round(f1, 3)  # NaN-safe
        if (f1 == f1) and f1 > best_f1:
            best_f1, best, best_name = f1, pipe, nm

    if best is None:
        result["message"] = "Could not fit any model (check your labels)."
        return result

    best.fit(X, y)
    with open(MODEL_OUT, "wb") as f:
        pickle.dump(best, f)
    META_OUT.write_text(json.dumps({
        "model_name": best_name, "granularity": "chunk_3s",
        "n_samples": int(len(X)), "n_safe": n_safe, "n_danger": n_danger,
        "cv_f1_macro": round(best_f1, 3),
        "trained_at": datetime.now().isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")

    result["ok"] = True
    result["cv_report"] = cv_report
    result["model"] = {"name": best_name, "cv_f1_macro": round(best_f1, 3),
                       "path": str(MODEL_OUT)}
    msg = (f"Trained {best_name} on {int(len(X))} chunks "
           f"(SAFE={n_safe}, DANGER={n_danger}); CV F1={best_f1:.2f}. "
           f"Saved to danger_classifier_chunks.pkl (whole-file model untouched).")
    if n_danger < 10:
        msg += " Note: danger class still small -- it improves with more danger journeys."
    result["message"] = msg
    return result


def main():
    print("\n" + "=" * 62)
    print("  Training CHUNK model from your labeled journeys")
    print("=" * 62)
    res = run_training()
    print(f"\nJourneys: {res['n_journeys']}  "
          f"chunks: SAFE={res['n_safe']} DANGER={res['n_danger']}")
    for name, c in res["per_journey"].items():
        print(f"   {str(name)[:48]:48s} safe={c['SAFE']:3d} "
              f"danger={c['DANGER']:3d} skip={c['SKIP']:3d}")
    if res["cv_report"]:
        print("\nCross-validating (F1 macro):")
        for nm, f1 in res["cv_report"].items():
            print(f"   {nm:14s} F1(macro)={'n/a' if f1 is None else f'{f1:.3f}'}")
    print("\n" + "-" * 62)
    print("  " + res["message"])
    print("-" * 62)


if __name__ == "__main__":
    main()
