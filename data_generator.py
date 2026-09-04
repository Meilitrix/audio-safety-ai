"""
data_generator.py — Generate Synthetic Audio Dataset
=====================================================
This script creates fake audio clips so you can train a model
WITHOUT needing to collect real recordings first.

Safe sounds  → low-pitched hums + gentle tones  (engine, radio, calm talk)
Danger sounds → loud bursts + sharp spikes       (shouting, crashes, screams)

Run this file directly:
    python data_generator.py
"""

import os
import numpy as np
import soundfile as sf          # saves numpy arrays as .wav files

# Import settings from config.py
from config import (
    SAFE_SOUNDS_DIR,
    DANGER_SOUNDS_DIR,
    SAMPLE_RATE,
    AUDIO_DURATION,
    N_SAMPLES_PER_CLASS,
)


def generate_safe_sound(duration=AUDIO_DURATION, sr=SAMPLE_RATE):
    """
    Create a synthetic "safe" audio clip.

    We mix together:
      • A low rumble  (simulates engine noise)
      • A soft sine wave (simulates radio / calm voice hum)
      • A tiny bit of random hiss (simulates ambient car noise)

    Parameters
    ----------
    duration : float  – length of the clip in seconds
    sr       : int    – sample rate (samples per second)

    Returns
    -------
    numpy array of audio samples, values between -1 and 1
    """
    n_samples = int(duration * sr)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # 1. Engine-like low rumble: 60–120 Hz sine wave
    engine_freq = np.random.uniform(60, 120)
    engine = 0.3 * np.sin(2 * np.pi * engine_freq * t)

    # 2. Soft tone: 200–500 Hz (mimics calm talking or radio music)
    tone_freq = np.random.uniform(200, 500)
    tone = 0.15 * np.sin(2 * np.pi * tone_freq * t)

    # 3. Background hiss (very quiet random noise)
    hiss = 0.05 * np.random.randn(n_samples)

    # Mix everything together
    audio = engine + tone + hiss

    # Normalise so the loudest peak is exactly 1.0
    audio = audio / np.max(np.abs(audio))
    return audio


def generate_danger_sound(duration=AUDIO_DURATION, sr=SAMPLE_RATE):
    """
    Create a synthetic "danger" audio clip.

    We mix together:
      • A loud, harsh burst (simulates shouting / screaming)
      • Sharp transient spikes (simulates crashing / slamming)
      • High-pitched wail  (simulates sirens or panicked voices)

    Parameters
    ----------
    duration : float  – length of the clip in seconds
    sr       : int    – sample rate (samples per second)

    Returns
    -------
    numpy array of audio samples, values between -1 and 1
    """
    n_samples = int(duration * sr)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # 1. Harsh burst: loud noise in 300–1500 Hz range (shouting)
    shout_freq = np.random.uniform(300, 1500)
    shout = 0.7 * np.sin(2 * np.pi * shout_freq * t)
    # Add amplitude modulation to make it sound more like yelling
    mod_freq = np.random.uniform(3, 10)
    shout *= (1 + np.sin(2 * np.pi * mod_freq * t))

    # 2. Sharp crash: sudden spike of noise at a random point
    crash_pos = np.random.randint(n_samples // 4, 3 * n_samples // 4)
    crash_len = int(0.1 * sr)  # 100 ms crash
    crash = np.zeros(n_samples)
    crash[crash_pos:crash_pos + crash_len] = (
        np.random.randn(crash_len) * 0.9
    )

    # 3. High-pitched wail: 800–2000 Hz sweep (scream / siren)
    wail_freq = np.linspace(800, 2000, n_samples)
    wail = 0.4 * np.sin(2 * np.pi * np.cumsum(wail_freq) / sr)

    # Mix everything together
    audio = shout + crash + wail

    # Normalise
    audio = audio / np.max(np.abs(audio))
    return audio


def generate_dataset(n_samples=N_SAMPLES_PER_CLASS):
    """
    Generate and save synthetic audio clips to disk.

    Creates `n_samples` safe clips and `n_samples` danger clips,
    saving them as .wav files in the data/ folders.
    """
    # Make sure the folders exist
    os.makedirs(SAFE_SOUNDS_DIR, exist_ok=True)
    os.makedirs(DANGER_SOUNDS_DIR, exist_ok=True)

    print(f"🔊 Generating {n_samples} SAFE sound clips...")
    for i in range(n_samples):
        audio = generate_safe_sound()
        filepath = os.path.join(SAFE_SOUNDS_DIR, f"safe_{i:04d}.wav")
        sf.write(filepath, audio, SAMPLE_RATE)
    print(f"   ✅ Saved {n_samples} safe clips → {SAFE_SOUNDS_DIR}")

    print(f"🔊 Generating {n_samples} DANGER sound clips...")
    for i in range(n_samples):
        audio = generate_danger_sound()
        filepath = os.path.join(DANGER_SOUNDS_DIR, f"danger_{i:04d}.wav")
        sf.write(filepath, audio, SAMPLE_RATE)
    print(f"   ✅ Saved {n_samples} danger clips → {DANGER_SOUNDS_DIR}")

    total = n_samples * 2
    print(f"\n🎉  Dataset ready!  {total} total clips generated.")
    print(f"    • Safe:   {n_samples} clips in  {SAFE_SOUNDS_DIR}")
    print(f"    • Danger: {n_samples} clips in  {DANGER_SOUNDS_DIR}")


# ── Allow running this file directly ─────────────────────────────────
if __name__ == "__main__":
    generate_dataset()
