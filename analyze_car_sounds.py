"""
analyze_car_sounds.py — Run YAMNet on car audio recordings, chunk by chunk.
Shows what the AI hears in each 3-second window.
"""
import os, sys, csv, io, warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import numpy as np
import librosa
import tensorflow as tf
import tensorflow_hub as hub
import urllib.request

# ── Load YAMNet ──
print("Loading YAMNet...")
model = hub.load("https://tfhub.dev/google/yamnet/1")

# ── Load class names from local file ──
from yamnet_classes import YAMNET_CLASS_NAMES
class_names = YAMNET_CLASS_NAMES
print(f"Loaded {len(class_names)} classes (local)")

# ── Danger classes ──
DANGER_INDICES = {
    386: "Scream", 387: "Shriek",
    10: "Shout", 13: "Yell",
    393: "Crash", 394: "Collapse",
}

# ── Files to analyze ──
BASE = os.path.dirname(os.path.abspath(__file__))
SFX_DIR = os.path.join(BASE, "sfx_training")

files = []
for root, dirs, fnames in os.walk(SFX_DIR):
    for fn in sorted(fnames):
        if fn.endswith((".mp3", ".wav", ".ogg", ".flac")):
            files.append(os.path.join(root, fn))
files.sort()

if not files:
    print("No audio files found in sfx_training/")
    sys.exit(1)

CHUNK_SEC = 3
SR = 16000

for fpath in files:
    rel = os.path.relpath(fpath, SFX_DIR)
    fname = os.path.basename(fpath)
    short = fname[:65] + "..." if len(fname) > 65 else fname

    print()
    print("=" * 80)
    print(f"  [{rel}]")
    print("=" * 80)

    audio, sr = librosa.load(fpath, sr=SR, mono=True, dtype=np.float32)
    duration = len(audio) / SR
    n_chunks = int(duration / CHUNK_SEC)
    print(f"  Duration: {duration:.1f}s  |  Chunks: {n_chunks} x {CHUNK_SEC}s  |  SR: {sr}")
    print("-" * 80)
    print(f"  {'Chunk':<7} {'Time':<10} {'Energy':<10} {'Peak':<8} {'Top Sound':<30} {'Score':<7} {'Status'}")
    print("-" * 80)

    danger_count = 0
    safe_count = 0

    for i in range(n_chunks):
        start = i * CHUNK_SEC * SR
        end = start + CHUNK_SEC * SR
        chunk = audio[start:end]

        # Energy analysis
        energy = np.mean(chunk ** 2)
        peak = np.max(np.abs(chunk))

        # YAMNet classification
        scores, embeddings, spectrogram = model(chunk)
        scores_np = scores.numpy()
        mean_scores = scores_np.mean(axis=0)

        # Top 3 sounds
        top3_idx = np.argsort(mean_scores)[::-1][:3]
        top_idx = top3_idx[0]
        top_score = mean_scores[top_idx]
        top_name = class_names[top_idx]

        # Check danger
        status = "SAFE"
        danger_sound = ""
        for did, dname in DANGER_INDICES.items():
            if mean_scores[did] > 0.5:
                status = "DANGER"
                danger_sound = dname
                break

        if status == "DANGER":
            danger_count += 1
        else:
            safe_count += 1

        time_str = f"{i*CHUNK_SEC:02d}-{(i+1)*CHUNK_SEC:02d}s"
        marker = " <<<" if status == "DANGER" else ""
        top3_str = ", ".join([f"{class_names[idx]}({mean_scores[idx]:.0%})" for idx in top3_idx])

        print(f"  #{i+1:<5} {time_str:<10} {energy:<10.6f} {peak:<8.4f} {top_name:<30} {top_score:<7.0%} {status}{marker}")
        if i < 3 or status == "DANGER":  # Show top-3 for first 3 chunks and any danger
            print(f"         Top 3: {top3_str}")

    print("-" * 80)
    print(f"  SUMMARY: {safe_count} SAFE, {danger_count} DANGER out of {n_chunks} chunks")
    print()

print("=" * 80)
print("  Analysis complete.")
print("=" * 80)
