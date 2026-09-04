"""
config.py — Central Configuration File
=======================================
All tunable settings live here so you never have to dig through
other files to change something.  Think of this as the "control panel"
for the whole project.
"""

import os

# ── Paths ────────────────────────────────────────────────────────────
# Where this file lives (the project root folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Raw audio clips will be stored here
DATA_DIR = os.path.join(BASE_DIR, "data")
SAFE_SOUNDS_DIR = os.path.join(DATA_DIR, "safe_sounds")
DANGER_SOUNDS_DIR = os.path.join(DATA_DIR, "danger_sounds")

# Trained model will be saved here
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "safety_classifier.pkl")

# ── Audio Settings ───────────────────────────────────────────────────
SAMPLE_RATE = 22050        # Samples per second (CD quality is 44100, 
                           # 22050 is plenty for speech/shout detection)
AUDIO_DURATION = 3         # Seconds per audio clip
N_MFCC = 20                # Number of MFCC features to extract
                           # (MFCCs = the "fingerprint" of a sound)

# ── Training Settings ────────────────────────────────────────────────
TEST_SIZE = 0.2            # 20% of data reserved for testing
RANDOM_STATE = 42          # Seed for reproducible results
N_SAMPLES_PER_CLASS = 50   # How many synthetic clips to generate

# ── Real-Time Detection Settings ─────────────────────────────────────
CHUNK_DURATION = 3         # Seconds of audio to analyse per chunk
CONFIDENCE_THRESHOLD = 0.6 # Minimum confidence to call "Danger"
                           # (0.0–1.0 — higher = stricter alerts)
CONTINUOUS_ALERT_SECONDS = 5  # Cooldown between repeated alerts

# ── Alert / Emergency Centre Settings ────────────────────────────────
# Replace with your real emergency-centre webhook URL
ALERT_WEBHOOK_URL = "https://your-emergency-centre.com/api/alert"
ALERT_ENABLED = True       # Set False to test without sending real alerts
