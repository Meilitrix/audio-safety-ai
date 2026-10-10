"""_whisper_probe.py - MEASUREMENT ONLY.  Nothing in the app imports this file.

Answers three questions before any wiring is attempted:
  1. Is Whisper installed on this machine, and are model weights cached offline?
  2. How many seconds does it take per 3-second chunk on this CPU?  (the dial
     gets a chunk every 3 s, so anything over ~2.5 s per chunk cannot run live)
  3. When it hears Urdu / Pashto / Punjabi, does it write the words back in
     native script or roman letters?  (the distress dictionary is written in
     roman letters - if the output is Arabic script, matching fails no matter
     how good the transcription is)
"""
import os
import sys
import time
import glob

import numpy as np

print("=" * 66)
print(" 1. IS WHISPER HERE, AND IS IT CACHED OFFLINE?")
print("=" * 66)
try:
    import whisper
except Exception as e:
    print("  whisper NOT importable:", type(e).__name__, e)
    sys.exit(0)
print("  whisper import OK, version:", getattr(whisper, "__version__", "?"))

cache = os.path.join(os.environ.get("USERPROFILE", ""), ".cache", "whisper")
if os.path.isdir(cache):
    for f in sorted(os.listdir(cache)):
        p = os.path.join(cache, f)
        print("  cached: %-18s %6.1f MB" % (f, os.path.getsize(p) / 1e6))
else:
    print("  no cache dir at", cache, "- first use would DOWNLOAD (needs internet)")

print()
print("=" * 66)
print(" 2 + 3. SPEED AND OUTPUT SCRIPT, ON YOUR OWN RECORDINGS")
print("=" * 66)
import librosa

wavs = sorted(glob.glob("saved_journeys/*.wav"))
if not wavs:
    print("  no journeys found")
    sys.exit(0)

t0 = time.time()
model = whisper.load_model("base")
print("  loading model 'base' took %.1f s (once, at start-up)" % (time.time() - t0))

# Pick a danger journey (most likely to contain speech) and a safe one.
target = None
for w in wavs:
    side = w.replace(".wav", ".label.json")
    try:
        import json
        lab = json.load(open(side, encoding="utf-8")).get("label")
    except Exception:
        continue
    if lab == "danger":
        target = w
        break
if target is None:
    target = wavs[0]
print("  test file:", os.path.basename(target))

y, sr = librosa.load(target, sr=16000, mono=True)
dur = len(y) / sr
print("  %.0f s of audio, resampled to 16 kHz" % dur)

# Slice it into 3 s chunks like the dial does, and time each one alone.
chunk = 3 * sr
n = int(len(y) // chunk)
times = []
texts = []
print()
print("  per-chunk timing (3 s of audio each):")
for i in range(min(n, 8)):
    seg = y[i * chunk:(i + 1) * chunk]
    t1 = time.time()
    r = model.transcribe(seg, fp16=False)
    el = time.time() - t1
    times.append(el)
    txt = (r.get("text") or "").strip()
    texts.append(txt)
    print("    chunk %d : %5.2f s   ->  %r" % (i, el, txt[:70]))

print()
print("  median per 3 s chunk : %.2f s" % float(np.median(times)))
print("  slowest              : %.2f s" % max(times))
budget = 3.0
if float(np.median(times)) <= 2.5:
    print("  VERDICT: fast enough to run live alongside the dial.")
elif float(np.median(times)) <= budget:
    print("  VERDICT: borderline - only worth it if it runs on a side thread.")
else:
    print("  VERDICT: TOO SLOW to transcribe every chunk live.")

# Same audio, longer window: does batching in 10 s pieces beat 3 s pieces?
t1 = time.time()
big = model.transcribe(y[: 10 * sr], fp16=False)
print("  one 10 s window      : %.2f s -> text %r" % (time.time() - t1, (big.get("text") or "").strip()[:80]))

print()
print("  --- what script does it write? (this decides whether the dictionary can match) ---")
for i, t in enumerate(texts):
    if t:
        nonascii = [c for c in t if ord(c) > 127]
        print("  chunk %d : %s%s" % (i, t[:60], "   <-- NON-LATIN CHARS: %r" % nonascii[:8] if nonascii else ""))

print()
print("  --- force the languages you actually need, on a longer slice ---")
for lang in ("ur", "en"):
    try:
        t1 = time.time()
        r = model.transcribe(y[: 12 * sr], fp16=False, language=lang)
        print("  language=%s : %.1f s -> %r" % (lang, time.time() - t1, (r.get("text") or "").strip()[:90]))
    except Exception as e:
        print("  language=%s failed: %s" % (lang, e))

try:
    t1 = time.time()
    r = model.transcribe(y[: 12 * sr], fp16=False)
    print("  auto-detect : %.1f s -> detected %s -> %r"
          % (time.time() - t1, r.get("language"), (r.get("text") or "").strip()[:90]))
except Exception as e:
    print("  auto-detect failed:", e)

tiny = whisper.load_model("tiny")
t1 = time.time()
r = tiny.transcribe(y[: 12 * sr], fp16=False)
print("  TINY model, same 12 s : %.1f s -> %r" % (time.time() - t1, (r.get("text") or "").strip()[:90]))
print("=" * 66)
