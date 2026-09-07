"""
full_audio_audit.py — Run ALL sfx_training sounds through:
  1. YAMNet classification (what sound does AI hear?)
  2. Energy/Peak analysis (how loud/sharp is it?)
  3. Danger Scoring Engine (what does the dial say?)

This shows the FULL capability of the current system.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import numpy as np
import librosa
import tensorflow_hub as hub

# Load scoring engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scoring_engine import DangerScorer

# Load YAMNet
print("Loading YAMNet...")
model = hub.load("https://tfhub.dev/google/yamnet/1")
from yamnet_classes import YAMNET_CLASS_NAMES
class_names = YAMNET_CLASS_NAMES
print(f"Loaded {len(class_names)} classes\n")

# Scan all audio files
BASE = os.path.dirname(os.path.abspath(__file__))
SFX_DIR = os.path.join(BASE, "sfx_training")

files = []
for root, dirs, fnames in os.walk(SFX_DIR):
    for fn in sorted(fnames):
        if fn.endswith((".mp3", ".wav", ".ogg", ".flac", ".aiff", ".m4a")):
            files.append(os.path.join(root, fn))
files.sort()

CHUNK_SEC = 3
SR = 16000

# Summary counters
folder_stats = {}

for fpath in files:
    rel = os.path.relpath(fpath, SFX_DIR)
    folder = rel.split(os.sep)[0]
    fname = os.path.basename(fpath)

    if folder not in folder_stats:
        folder_stats[folder] = {"files": 0, "chunks": 0, "normal": 0,
                                 "concerning": 0, "elevated": 0,
                                 "high_risk": 0, "critical": 0}
    folder_stats[folder]["files"] += 1

    print()
    print("=" * 90)
    print(f"  [{rel}]")
    print("=" * 90)

    try:
        audio, sr = librosa.load(fpath, sr=SR, mono=True, dtype=np.float32)
    except Exception as e:
        print(f"  ERROR loading: {e}")
        continue

    duration = len(audio) / SR
    n_chunks = max(1, int(duration / CHUNK_SEC))
    print(f"  Duration: {duration:.1f}s  |  Chunks: {n_chunks} x {CHUNK_SEC}s")
    print("-" * 90)
    print(f"  {'#':<4} {'Energy':<10} {'Peak':<8} {'YAMNet hears':<28} "
          f"{'Voice':<6} {'Event':<6} {'Score':<8} {'DIAL'}")
    print("-" * 90)

    scorer = DangerScorer()

    for i in range(n_chunks):
        start = i * CHUNK_SEC * SR
        end = min(start + CHUNK_SEC * SR, len(audio))
        chunk = audio[start:end]

        if len(chunk) < SR:  # skip tiny last chunk
            continue

        # Energy/peak
        energy = float(np.mean(chunk ** 2))
        peak = float(np.max(np.abs(chunk)))

        # YAMNet
        scores, embeddings, spectrogram = model(chunk)
        scores_np = scores.numpy()
        mean_scores = scores_np.mean(axis=0)
        top_idx = int(np.argsort(mean_scores)[::-1][0])
        top_score = float(mean_scores[top_idx])
        top_name = class_names[top_idx]

        # Scoring engine
        result = scorer.process_chunk(
            word_severity=0,  # no speech keywords in SFX
            energy=energy,
            peak=peak,
            yamnet_top_name=top_name,
        )

        label = result["dial_label"]
        folder_stats[folder]["chunks"] += 1
        label_key = label.lower().replace(" ", "_")
        folder_stats[folder][label_key] = \
            folder_stats[folder].get(label_key, 0) + 1

        voice_s = result["voice_severity"]
        event_s = result["event_severity"]
        acc = result["accumulated_score"]

        # Marker for interesting chunks
        marker = ""
        if label in ("HIGH RISK", "CRITICAL"):
            marker = " <<<"
        elif label == "ELEVATED":
            marker = " <<"

        print(f"  #{i+1:<3} {energy:<10.5f} {peak:<8.3f} {top_name:<28} "
              f"{voice_s:<6} {event_s:<6} {acc:<8.2f} {label}{marker}")

    final = scorer.get_state()
    print("-" * 90)
    print(f"  FINAL DIAL: {final['dial_label']} (score={final['accumulated_score']:.2f})")
    print()

# ── OVERALL SUMMARY ──
print()
print("=" * 90)
print("  OVERALL AUDIT SUMMARY")
print("=" * 90)
print(f"  {'Folder':<20} {'Files':<6} {'Chunks':<7} {'Normal':<8} "
      f"{'Concrn':<8} {'Elevtd':<8} {'HighR':<8} {'Crit':<8}")
print("-" * 90)
total_chunks = 0
total_normal = 0
total_danger = 0
for folder in sorted(folder_stats.keys()):
    s = folder_stats[folder]
    total_chunks += s["chunks"]
    total_normal += s["normal"]
    non_normal = s["chunks"] - s["normal"]
    total_danger += non_normal
    print(f"  {folder:<20} {s['files']:<6} {s['chunks']:<7} {s['normal']:<8} "
          f"{s.get('concerning',0):<8} {s.get('elevated',0):<8} "
          f"{s.get('high_risk',0):<8} {s.get('critical',0):<8}")
print("-" * 90)
print(f"  {'TOTAL':<20} {sum(s['files'] for s in folder_stats.values()):<6} "
      f"{total_chunks:<7} {total_normal:<8} {total_danger:<8}")
print()
pct = (total_normal / total_chunks * 100) if total_chunks > 0 else 0
print(f"  Safe sounds classified as NORMAL: {total_normal}/{total_chunks} ({pct:.1f}%)")
print(f"  Danger sounds detected (non-NORMAL): {total_danger}/{total_chunks} ({100-pct:.1f}%)")
print()
