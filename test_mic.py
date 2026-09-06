"""
test_mic.py — Microphone & AI Diagnostic Tool
================================================
Run this in your terminal to verify:
  1. Your microphone is actually capturing audio
  2. YAMNet is processing real sound
  3. Distress keywords are being detected

Usage:
    python test_mic.py

Speak normally, then scream or say "help" — watch the output change.
Press Ctrl+C to stop.
"""

import os
import sys
import time
import numpy as np

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

print()
print("=" * 60)
print("  MICROPHONE & AI DIAGNOSTIC TOOL")
print("=" * 60)
print()

# ── Step 1: Check microphone ────────────────────────────────────────
print("[1/3] Checking microphone...")
try:
    import sounddevice as sd
    devices = sd.query_devices()
    input_devices = [d for d in devices if d["max_input_channels"] > 0]

    if not input_devices:
        print("  ❌ NO microphone found! Connect a mic and try again.")
        sys.exit(1)

    print(f"  ✅ Found {len(input_devices)} input device(s):")
    for d in input_devices:
        print(f"     • {d['name']} ({d['max_input_channels']} channels)")

    # Record 1 second of audio to verify
    print("  🎤 Recording 1 second of test audio...")
    audio = sd.rec(
        int(1 * 22050),
        samplerate=22050,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    audio = audio.flatten()

    energy = np.mean(audio ** 2)
    peak = np.max(np.abs(audio))
    print(f"  ✅ Audio captured!  Energy: {energy:.6f}  Peak: {peak:.4f}")

    if energy < 0.00001:
        print("  ⚠️  Audio is nearly silent. Check your mic volume/gain.")
    elif energy > 0.1:
        print("  🔊 Audio is very loud — good signal!")
    else:
        print("  ✅ Audio level looks normal.")

except Exception as e:
    print(f"  ❌ Microphone error: {e}")
    sys.exit(1)

# ── Step 2: Check YAMNet ────────────────────────────────────────────
print()
print("[2/3] Loading YAMNet model...")
try:
    from yamnet_engine import classify_audio, _load_model
    _load_model()
    print("  ✅ YAMNet loaded successfully!")

    # Classify the test audio we just recorded
    print("  🔍 Classifying the test audio we just recorded...")
    result = classify_audio(audio, sr=22050)
    print(f"     Status:   {result['status']}")
    print(f"     Sound:    {result['sound_name']}")
    print(f"     Confidence: {result['confidence']*100:.1f}%")
    print(f"     YAMNet raw: {result['yamnet_raw']['class']} "
          f"(score: {result['yamnet_raw']['score']*100:.1f}%)")

except Exception as e:
    print(f"  ❌ YAMNet error: {e}")
    import traceback
    traceback.print_exc()

# ── Step 3: Live monitoring ─────────────────────────────────────────
print()
print("[3/3] Starting LIVE monitoring (speak, then scream for testing)...")
print("      Press Ctrl+C to stop.")
print()
print("  " + "─" * 56)
print(f"  {'TIME':<10} {'STATUS':<8} {'CONF':<7} {'SOUND':<25} {'TRANSCRIPT'}")
print("  " + "─" * 56)

try:
    from yamnet_engine import classify_audio
    while True:
        # Record 2 seconds
        audio = sd.rec(
            int(2 * 16000),
            samplerate=16000,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        audio = audio.flatten()

        # Classify
        result = classify_audio(audio, sr=16000)

        # Get transcript
        transcript = ""
        speech = result.get("speech_info", {})
        if speech.get("transcript"):
            transcript = speech["transcript"][:30]
            if speech.get("keywords"):
                transcript += f" 🚨{speech['keywords']}"

        status_icon = "🚨" if result["status"] == "DANGER" else "✅"
        now = time.strftime("%H:%M:%S")

        print(
            f"  {now:<10} {status_icon} {result['status']:<6} "
            f"{result['confidence']*100:>5.1f}%  "
            f"{result['sound_name']:<25} "
            f"{transcript}"
        )

except KeyboardInterrupt:
    print("\n\n  🛑 Diagnostic stopped.")
    print()
