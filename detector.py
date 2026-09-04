"""
detector.py — Real-Time Detection with Smoothing Buffer
=========================================================
Key stability rule:  DANGER must be detected in TWO CONSECUTIVE
audio chunks before the dashboard status flips.  A single spike
(finger scratch, mouth noise, door close) is ignored.

Each chunk is ~2–3 seconds, so two consecutive = ~4–6 seconds
of sustained danger before an alert fires.
"""

import io
import wave
import base64
import numpy as np
import sounddevice as sd

from config import SAMPLE_RATE, CHUNK_DURATION, CONFIDENCE_THRESHOLD
from yamnet_engine import classify_audio
from alert_system import AlertSystem


# ══════════════════════════════════════════════════════════════════════
#  SMOOTHING BUFFER — the anti-false-positive layer
# ══════════════════════════════════════════════════════════════════════

class DetectionBuffer:
    """
    Keeps the last N detection results and only confirms DANGER
    when the most recent `required_consecutive` results are ALL DANGER.

    This prevents a single 2-second spike from triggering an alert.
    """

    def __init__(self, size=3, required_consecutive=2):
        self.size = size
        self.required = required_consecutive
        self._history = []          # list of result dicts

    def add(self, result):
        """Add a new detection result to the buffer."""
        self._history.append(result)
        self._history = self._history[-self.size:]

    @property
    def stable_status(self):
        """
        Return the smoothed status.
        DANGER only if the last `required` chunks were ALL DANGER.
        """
        if len(self._history) < self.required:
            return "SAFE"

        recent = self._history[-self.required:]
        all_danger = all(r["status"] == "DANGER" for r in recent)
        return "DANGER" if all_danger else "SAFE"

    @property
    def latest(self):
        """Return the most recent raw result."""
        return self._history[-1] if self._history else None

    def clear(self):
        self._history = []


# ══════════════════════════════════════════════════════════════════════
#  SINGLE LISTEN + CLASSIFY
# ══════════════════════════════════════════════════════════════════════

def listen_once(duration=CHUNK_DURATION, sr=SAMPLE_RATE):
    """
    Record `duration` seconds from the microphone and classify.

    Returns the raw result dict from yamnet_engine.classify_audio.
    """
    n_samples = int(duration * sr)
    audio = sd.rec(n_samples, samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    audio = audio.flatten()

    result = classify_audio(audio, sr)
    return result


# ══════════════════════════════════════════════════════════════════════
#  STABILISED LISTEN — applies the smoothing buffer
# ══════════════════════════════════════════════════════════════════════

_buffer = DetectionBuffer(size=3, required_consecutive=2)


def listen_stable(duration=CHUNK_DURATION, sr=SAMPLE_RATE,
                  threshold=CONFIDENCE_THRESHOLD, alert_system=None):
    """
    Record → classify → smooth → optionally alert.

    The returned dict has an extra key `stable_status` which is the
    buffer-smoothed result.  The dashboard should display THIS, not
    the raw `status`.

    Returns
    -------
    dict with all keys from classify_audio PLUS:
        stable_status : "SAFE" | "DANGER" — the smoothed decision
        raw_status    : "SAFE" | "DANGER" — the single-chunk decision
    """
    if alert_system is None:
        alert_system = AlertSystem()

    # ── Record & classify ───────────────────────────────────────────
    result = listen_once(duration, sr)

    # ── Add to smoothing buffer ─────────────────────────────────────
    _buffer.add(result)
    stable = _buffer.stable_status

    result["raw_status"] = result["status"]
    result["stable_status"] = stable

    # ── Alert only on stable DANGER ─────────────────────────────────
    if stable == "DANGER" and result["confidence"] >= threshold:
        alert_system.send_alert(
            result["confidence"],
            details={
                "sound_detected": result["sound_name"],
                "raw_detections": [
                    r["status"] for r in _buffer._history[-2:]
                ],
            },
        )

    return result


# ══════════════════════════════════════════════════════════════════════
#  WAVEFORM-ONLY SNAPSHOT (for dashboard visualiser when idle)
# ══════════════════════════════════════════════════════════════════════

def get_waveform_snapshot(duration=0.5, sr=SAMPLE_RATE):
    """Quick mic grab — waveform only, no classification."""
    n_samples = int(duration * sr)
    audio = sd.rec(n_samples, samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    audio = audio.flatten()

    n_pts = 200
    step = max(1, len(audio) // n_pts)
    return [float(x) for x in np.abs(audio[::step])[:n_pts]]


# ══════════════════════════════════════════════════════════════════════
#  CONTINUOUS MONITOR (CLI mode)
# ══════════════════════════════════════════════════════════════════════

def run_continuous_monitor(chunk_duration=CHUNK_DURATION,
                           threshold=CONFIDENCE_THRESHOLD):
    """CLI loop: listen → stabilise → print → repeat."""
    from config import CHUNK_DURATION as DEFAULT_CHUNK
    duration = chunk_duration or DEFAULT_CHUNK
    alert_system = AlertSystem()

    print("\n" + "=" * 60)
    print("🚗  AUDIO SAFETY MONITOR — Stabilised Mode")
    print("=" * 60)
    print(f"   Chunk duration:   {duration}s")
    print(f"   Alert threshold:  {threshold * 100:.0f}%")
    print(f"   Smoothing buffer: 2 consecutive DANGER chunks required")
    print(f"   Press Ctrl+C to stop.\n")

    try:
        while True:
            result = listen_stable(
                duration=duration,
                threshold=threshold,
                alert_system=alert_system,
            )
            raw = result["raw_status"]
            stable = result["stable_status"]
            icon = "🚨" if stable == "DANGER" else "✅"
            print(
                f"  {icon}  stable={stable:6s}  raw={raw:6s}  "
                f"conf={result['confidence']*100:5.1f}%  "
                f"sound={result['sound_name']}"
            )
    except KeyboardInterrupt:
        print("\n\n🛑 Monitor stopped.")
        alert_system.summary()


if __name__ == "__main__":
    run_continuous_monitor()


# ══════════════════════════════════════════════════════════════════════
#  BROWSER CHUNK CLASSIFIER — handles base64 WAV from the web component
# ══════════════════════════════════════════════════════════════════════

def decode_wav_base64(b64_string):
    """
    Decode a base64-encoded WAV string into (numpy_float32_array, sample_rate).
    """
    wav_bytes = base64.b64decode(b64_string)
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
        # Convert Int16 PCM → Float32
        int16 = np.frombuffer(raw, dtype=np.int16)
        audio = int16.astype(np.float32) / 32768.0
    return audio, sr


def classify_browser_chunk(b64_wav, buffer=None, threshold=CONFIDENCE_THRESHOLD,
                           alert_system=None):
    """
    Classify a base64-encoded WAV chunk from the browser component.

    Returns
    -------
    dict with keys: status, stable_status, raw_status, confidence,
                    sound_name, speech_info, waveform, yamnet_raw
    """
    if alert_system is None:
        alert_system = AlertSystem()
    if buffer is None:
        buffer = DetectionBuffer(size=3, required_consecutive=2)

    # Decode WAV
    audio, sr = decode_wav_base64(b64_wav)

    # Classify via YAMNet
    result = classify_audio(audio, sr)

    # Smoothing buffer
    buffer.add(result)
    stable = buffer.stable_status

    result["raw_status"] = result["status"]
    result["stable_status"] = stable

    # Alert on stable DANGER
    if stable == "DANGER" and result["confidence"] >= threshold:
        alert_system.send_alert(
            result["confidence"],
            details={
                "sound_detected": result["sound_name"],
                "raw_detections": [
                    r["status"] for r in buffer._history[-2:]
                ],
            },
        )

    return result, audio, sr
