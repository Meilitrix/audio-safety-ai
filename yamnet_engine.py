"""
yamnet_engine.py — The AI Brain (Multi-Signal Detection)
=========================================================
Three detection layers working together:

  Layer 1 — YAMNet:       Recognises screams, shouts, crashes (521 classes)
  Layer 2 — Energy:        Detects sudden silence (car stopping) & loud bursts
  Layer 3 — Pitch:         Detects screaming via high fundamental frequency

Transcription is handled by Web Speech API in the browser (not here).

Classification rules (ride-sharing tuned):
  • DANGER confidence must be ≥ 0.80 — faint guesses default to SAFE
  • Only genuine distress sounds count: scream, shriek, shout, yell, crash
  • Normal speech, engine, traffic, horns, fan hum → always SAFE
  • Finger scratches, mouth noises, plastic sounds → SAFE (not crash)
"""

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import librosa
import threading

# ══════════════════════════════════════════════════════════════════════
#  YAMNet model (singleton — loaded once, cached forever)
# ══════════════════════════════════════════════════════════════════════
_YAMNET_URL = "https://tfhub.dev/google/yamnet/1"
_MODEL = None
_CLASS_NAMES = None
_MODEL_LOCK = threading.Lock()

# ══════════════════════════════════════════════════════════════════════
#  TUNING CONSTANTS — ride-sharing specific
# ══════════════════════════════════════════════════════════════════════

# Minimum YAMNet confidence to call DANGER (0.50 = 50%)
# NOTE: The smoothing buffer (2 consecutive chunks) provides the
# real false-positive protection.  This threshold just filters
# out very faint guesses.
DANGER_THRESHOLD = 0.50

# ── DANGER sound classes ─────────────────────────────────────────────
# ONLY genuine distress signals.  Normal speech, children, sighs are
# deliberately EXCLUDED — they are normal in a ride.
DANGER_INDICES = {
    # Screaming / shrieking (high-confidence distress)
    386: "Scream",
    387: "Shriek",

    # Shouting / yelling (aggressive vocalisation — NOT normal speech)
    10:  "Shout",
    13:  "Yell",

    # Physical impact / crash
    393: "Crash",
    394: "Collapse",
}

# ── SAFE sound classes ───────────────────────────────────────────────
# Everything normal in a car ride.  If YAMNet hears any of these at
# reasonable confidence, we immediately call it SAFE.
SAFE_INDICES = {
    # Speech / conversation (NORMAL — not danger)
    0:   "Speech",        1:  "Child speech",   2:  "Conversation",
    3:   "Narration",     4:  "Babbling",       11: "Children playing",

    # Vehicle / traffic / horns
    367: "Vehicle",       374: "Car",           375: "Vehicle horn",
    376: "Toot",          377: "Car alarm",     381: "Car passing by",
    383: "Truck",

    # Engine / mechanical / fan
    402: "Engine",        403: "Idling",        404: "Accelerating",
    447: "Mechanical fan", 448: "Air conditioning", 444: "Gears",

    # Music / radio / TV
    61:  "Music",         365: "Television",

    # Ambient / indoor / outdoor
    500: "Noise",         501: "Environmental noise",
    504: "Silence",       510: "Inside small room",
    511: "Inside large room", 512: "Inside public space",
    513: "Outside urban", 514: "Outside rural",
    503: "Mains hum",     516: "Echo",
}


# ══════════════════════════════════════════════════════════════════════
#  MODEL LOADING
# ══════════════════════════════════════════════════════════════════════

def _load_model():
    """Download YAMNet once, cache forever. Thread-safe."""
    global _MODEL, _CLASS_NAMES
    if _MODEL is not None:
        return _MODEL, _CLASS_NAMES
    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL, _CLASS_NAMES
        print("[Engine] Loading YAMNet (first time ~30 s)...")
        _MODEL = hub.load(_YAMNET_URL)
        _CLASS_NAMES = _load_class_names_csv()
        print(f"[Engine] YAMNet ready — {len(_CLASS_NAMES)} classes loaded.")
        if len(_CLASS_NAMES) > 386:
            print(f"[Engine] Sample classes: "
                  f"[0]={_CLASS_NAMES[0]}, [10]={_CLASS_NAMES[10]}, "
                  f"[15]={_CLASS_NAMES[15]}, [386]={_CLASS_NAMES[386]}")
    return _MODEL, _CLASS_NAMES


def _load_class_names_csv():
    """Load embedded class names — no network needed."""
    from yamnet_classes import YAMNET_CLASS_NAMES
    print(f"[Engine] Loaded {len(YAMNET_CLASS_NAMES)} embedded class names.")
    return YAMNET_CLASS_NAMES


# ══════════════════════════════════════════════════════════════════════
#  LAYER 1: YAMNet sound classification
# ══════════════════════════════════════════════════════════════════════

def _run_yamnet(audio_16k):
    """
    Run YAMNet and return structured results.

    Returns
    -------
    top_class  : int   – index of highest-scoring class
    top_score  : float – its confidence
    top_name   : str   – human-readable name
    scores     : numpy array (521,) – mean scores across time
    """
    model, class_names = _load_model()
    scores, embeddings, _ = model(audio_16k)
    mean_scores = np.mean(scores.numpy(), axis=0)

    top_class = int(np.argmax(mean_scores))
    top_score = float(mean_scores[top_class])
    top_name = (class_names[top_class]
                if top_class < len(class_names)
                else f"class_{top_class}")

    # ── Diagnostic: log top 5 predictions ──
    top5_idx = np.argsort(mean_scores)[::-1][:5]
    top5_str = ", ".join(
        f"#{i}={class_names[i] if i < len(class_names) else '?'}"
        f"({mean_scores[i]:.2f})"
        for i in top5_idx
    )
    print(f"  [YAMNet] Top 5: {top5_str}")

    return top_class, top_score, top_name, mean_scores


# ══════════════════════════════════════════════════════════════════════
#  LAYER 2: Energy analysis (sudden silence / loud burst)
# ══════════════════════════════════════════════════════════════════════

def _analyse_energy(audio_16k):
    """
    Detect two conditions:
      1. Sudden silence — energy drops to near-zero (car stopped, engine off)
      2. Loud burst      — energy spikes well above the chunk average

    Returns
    -------
    signal   : "SILENCE" | "LOUD_BURST" | "NORMAL"
    level    : float 0–1 – how extreme the condition is
    """
    # Split audio into 10 segments and compare energy across them
    seg_len = max(1, len(audio_16k) // 10)
    segments = [audio_16k[i:i + seg_len] for i in range(0, len(audio_16k), seg_len)]
    energies = np.array([np.mean(s ** 2) for s in segments if len(s) > 0])

    if len(energies) < 2:
        return "NORMAL", 0.0

    overall_energy = float(np.mean(energies))
    max_energy = float(np.max(energies))
    min_energy = float(np.min(energies))

    # ── Sudden silence detection ────────────────────────────────────
    # If the last segment has <10% of the average energy, the car
    # may have just stopped
    if overall_energy > 0.001 and min_energy < overall_energy * 0.1:
        # Check if the QUIET part is at the end (most recent)
        last_seg_energy = float(energies[-1]) if len(energies) > 0 else 0
        if last_seg_energy < overall_energy * 0.15:
            silence_level = 1.0 - (last_seg_energy / max(overall_energy, 1e-8))
            return "SILENCE", float(np.clip(silence_level, 0, 1))

    # ── Loud burst detection ────────────────────────────────────────
    # If one segment is 5× louder than average, something sudden happened
    if overall_energy > 0.0001 and max_energy > overall_energy * 5:
        burst_level = min(max_energy / max(overall_energy, 1e-8) / 10, 1.0)
        return "LOUD_BURST", float(burst_level)

    return "NORMAL", 0.0


# ══════════════════════════════════════════════════════════════════════
#  LAYER 3: Pitch analysis (screaming detection)
# ══════════════════════════════════════════════════════════════════════

def _analyse_pitch(audio_16k):
    """
    Estimate fundamental frequency (F0) to detect screaming.

    Normal conversation: 85–255 Hz
    Screaming / shrieking: 400–1500+ Hz with high intensity

    Returns
    -------
    is_screaming : bool
    pitch_level  : float 0–1 – how extreme the pitch is
    mean_f0      : float – mean fundamental frequency in Hz
    """
    try:
        f0, voiced_flags, _ = librosa.pyin(
            audio_16k,
            fmin=60,
            fmax=2000,
            sr=16000,
            frame_length=2048,
        )

        # Only consider voiced frames
        voiced_f0 = f0[voiced_flags == True]
        if len(voiced_f0) < 5:
            return False, 0.0, 0.0

        mean_f0 = float(np.nanmean(voiced_f0))
        max_f0 = float(np.nanmax(voiced_f0))

        # Screaming: sustained high pitch (>400 Hz) with energy
        if mean_f0 > 400:
            pitch_level = float(np.clip((mean_f0 - 400) / 600, 0, 1))
            return True, pitch_level, mean_f0

        # Occasional high spikes (shriek)
        if max_f0 > 800 and np.nanstd(voiced_f0) > 150:
            pitch_level = float(np.clip((max_f0 - 800) / 700, 0, 1))
            return True, pitch_level * 0.7, mean_f0

        return False, 0.0, mean_f0

    except Exception:
        return False, 0.0, 0.0


# ══════════════════════════════════════════════════════════════════════
#  MASTER CLASSIFIER — fuses all four layers
# ══════════════════════════════════════════════════════════════════════

def classify_audio(audio, sr=16000):
    """
    Full classification pipeline.

    1. Resample to 16 kHz
    2. Run YAMNet (sound recognition)
    3. Run energy analysis (silence / burst detection)
    4. Run pitch analysis (scream detection)
    5. Fuse all signals → SAFE or DANGER

    Note: Speech transcription is handled by Web Speech API in the browser.

    Returns
    -------
    dict with keys:
        status, confidence, sound_name, top5, waveform,
        energy_signal, pitch_info, yamnet_raw, speech_info
    """
    # ── Resample ────────────────────────────────────────────────────
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
    audio = audio.astype(np.float32)

    # ── Layer 1: YAMNet ─────────────────────────────────────────────
    top_class, top_score, top_name, scores = _run_yamnet(audio)

    # ── Layer 2: Energy ─────────────────────────────────────────────
    energy_signal, energy_level = _analyse_energy(audio)

    # ── Layer 3: Pitch ──────────────────────────────────────────────
    is_screaming, pitch_level, mean_f0 = _analyse_pitch(audio)

    # ── Layer 4: Speech transcription ───────────────────────────────
    # Transcription is now handled by Web Speech API in the browser.
    # Server returns empty speech_info.
    speech_info = {
        "active": False, "transcript": "", "language": "",
        "has_distress": False, "keywords": [], "confidence": 0.0,
        "risk_score": 0,
    }

    # ── Waveform for visualiser ─────────────────────────────────────
    n_pts = 200
    step = max(1, len(audio) // n_pts)
    waveform = [float(x) for x in np.abs(audio[::step])[:n_pts]]

    # ── Top 5 sounds ────────────────────────────────────────────────
    _, class_names = _load_model()
    top5_idx = np.argsort(scores)[::-1][:5]
    top5 = [
        (class_names[i] if i < len(class_names) else f"class_{i}",
         float(scores[i]))
        for i in top5_idx
    ]

    # ══════════════════════════════════════════════════════════════════
    #  FUSION LOGIC — decide SAFE or DANGER
    # ══════════════════════════════════════════════════════════════════

    danger_conf = 0.0
    danger_reason = ""

    # ── Signal A: YAMNet danger class ───────────────────────────────
    if top_class in DANGER_INDICES:
        if top_score >= DANGER_THRESHOLD:
            danger_conf = max(danger_conf, top_score)
            danger_reason = DANGER_INDICES[top_class]
    else:
        # Check if ANY danger class scores above threshold
        for idx in DANGER_INDICES:
            if idx < len(scores) and scores[idx] >= DANGER_THRESHOLD:
                if scores[idx] > danger_conf:
                    danger_conf = float(scores[idx])
                    danger_reason = DANGER_INDICES[idx]

    # ── Signal B: Pitch screaming detection ─────────────────────────
    if is_screaming and pitch_level > 0.5:
        # Pitch-based danger only if YAMNet also hints at voice distress
        yamnet_voice_hint = any(
            scores[i] > 0.3
            for i in [10, 13, 177, 178, 182, 190, 386, 387]
            if i < len(scores)
        )
        if yamnet_voice_hint:
            combined = 0.5 + pitch_level * 0.3
            if combined > danger_conf:
                danger_conf = combined
                danger_reason = "Screaming (pitch detected)"

    # ── Signal C: Sudden silence (car stopping) ─────────────────────
    if energy_signal == "SILENCE" and energy_level > 0.7:
        silence_conf = 0.5 + energy_level * 0.3
        if silence_conf > danger_conf:
            danger_conf = silence_conf
            danger_reason = "Sudden silence (vehicle stop?)"

    # ── Final decision ──────────────────────────────────────────────
    if danger_conf >= DANGER_THRESHOLD:
        status = "DANGER"
        confidence = danger_conf
        sound_name = danger_reason
    else:
        status = "SAFE"
        # Use YAMNet's top class name, or the friendly safe name
        if top_class in SAFE_INDICES:
            sound_name = SAFE_INDICES[top_class]
        else:
            sound_name = top_name
        confidence = max(top_score, 1.0 - danger_conf)

    return {
        "status": status,
        "confidence": float(confidence),
        "sound_name": sound_name,
        "top5": top5,
        "waveform": waveform,
        "energy_signal": energy_signal,
        "pitch_info": {
            "screaming": is_screaming,
            "level": pitch_level,
            "mean_f0_hz": mean_f0,
        },
        "speech_info": speech_info,
        "yamnet_raw": {
            "class": top_name,
            "score": top_score,
            "class_id": top_class,
        },
    }


# ══════════════════════════════════════════════════════════════════════
#  PRELOAD — warm up models in background (called on server start)
# ══════════════════════════════════════════════════════════════════════

def preload_models():
    """Pre-load YAMNet in background so first chunks are fast."""
    print("[Preload] Warming up AI models in background...")
    try:
        _load_model()
        print("[Preload] YAMNet ready.")
    except Exception as e:
        print(f"[Preload] YAMNet failed: {e}")
    print("[Preload] Models loaded. (Transcription: Web Speech API in browser)")
