"""
whisper_engine.py — Layer 4: Speech Recognition for Distress Keywords
=======================================================================
Uses OpenAI's Whisper (local, offline) to transcribe speech and scan
for distress keywords like "help!", "stop!", "no!", etc.

This fills the gap YAMNet cannot cover: understanding WHAT someone
is saying, not just HOW they sound.

Architecture:
    Microphone → YAMNet (sound classification)
               → Energy  (silence detection)
               → Pitch   (scream detection)
               → Whisper (distress keyword detection)  ← THIS MODULE
"""

import numpy as np
import threading

# ══════════════════════════════════════════════════════════════════════
#  DISTRESS KEYWORDS — multilingual
# ══════════════════════════════════════════════════════════════════════
# If any of these words appear in the transcription, it's a strong
# danger signal.  Add more for your target market's languages.

DISTRESS_KEYWORDS = [
    # ── English ──
    "help", "help me", "stop", "stop it", "no", "no no",
    "don't", "dont", "please stop", "please help",
    "call the police", "call police", "911",
    "he's crazy", "she's crazy", "get off",
    "let me go", "let me out", "don't touch",
    "i'm scared", "im scared", "i'm afraid",
    "danger", "emergency", "hurt", "hurting",
    "assault", "rape", "kidnap", "weapon", "knife", "gun",
    "drive safe", "slow down", "watch out",

    # ── Spanish ──
    "ayuda", "ayúdame", "para", "no no", "policía",
    "déjame", "tengo miedo", "socorro", "emergencia",

    # ── French ──
    "aide", "aidez-moi", "arrêtez", "police", "au secours",
    "j'ai peur", "urgence",

    # ── Portuguese ──
    "ajuda", "me ajuda", "para", "polícia", "socorro",
    "tenho medo", "emergência",

    # ── Arabic (transliterated) ──
    "help", "waqf", "birji", "mousa3ada",

    # ── Urdu (اردو) — Pakistan ──
    # Roman Urdu (how people type/say it):
    "bachao", "bachao mujhe", "madad", "madad karo",
    "ruko", "ruko jao", "nahi", "nahi nahi",
    "please ruko", "mujhe choro", "mujhe chhod do",
    "police bulao", "police ko call karo",
    "dar lag raha hai", "mujhe dar lag raha hai",
    "mat chuo", "mujhe mat chuo",
    "mara", "maar diya", "chaku", "bandook",
    "kidnapping", "aghwa",
    # Urdu script:
    "بچاؤ", "مدد", "رکو", "نہیں",
    "مجھے چھوڑو", "پولیس",
    # ── Punjabi (Pakistan) ──
    "bacha", "bacha lao", "madad karo", "ruk jao",
    "menu chhod do", "menu bachao",
    # ── Pashto ──
    "help", "madad", "wadre", "police",
]

# Minimum Whisper confidence to trust the transcription (0–1)
TRANSCRIPTION_CONFIDENCE = 0.3

# ══════════════════════════════════════════════════════════════════════
#  KEYWORD SEVERITY — maps keywords to risk levels (0-4)
# ══════════════════════════════════════════════════════════════════════
# Level 0 = Normal, Level 1 = Concerning, Level 2 = Elevated,
# Level 3 = High Risk, Level 4 = Critical
KEYWORD_SEVERITY = {
    # ── Level 3 — High Risk (direct distress) ──
    "help": 3, "help me": 3, "please help": 3,
    "bachao": 3, "bachao mujhe": 3, "madad": 3, "madad karo": 3,
    "ayuda": 3, "socorro": 3, "aide": 3, "ajuda": 3,
    "let me go": 3, "let me out": 3,
    "i'm scared": 3, "im scared": 3, "i'm afraid": 3,
    "rape": 3, "kidnap": 3, "weapon": 3, "knife": 3, "gun": 3,
    "police bulao": 3, "police ko call karo": 3,
    "maar diya": 3, "chaku": 3, "bandook": 3, "aghwa": 3,

    # ── Level 2 — Elevated (asking to stop, distress-adjacent) ──
    "stop": 2, "stop it": 2, "please stop": 2,
    "ruko": 2, "ruko jao": 2, "please ruko": 2,
    "no": 2, "no no": 2, "nahi": 2, "nahi nahi": 2,
    "don't": 2, "dont": 2, "don't touch": 2,
    "para": 2, "arrêtez": 2, "mujhe choro": 2, "mujhe chhod do": 2,
    "mat chuo": 2, "mujhe mat chuo": 2,
    "dar lag raha hai": 2, "mujhe dar lag raha hai": 2,
    "menu chhod do": 2, "menu bachao": 2,

    # ── Level 1 — Concerning (context-dependent) ──
    "yahan ruk jao": 1, "yahan ruk jao bhai": 1,
    "ruk jao": 1, "stop here": 1,
    "drive safe": 1, "slow down": 1, "watch out": 1,
    "call the police": 1, "call police": 1,
    "he's crazy": 1, "she's crazy": 1, "get off": 1,
    "emergency": 1, "hurt": 1, "hurting": 1,
    "assault": 1, "kidnapping": 1,
    "bacha": 1, "bacha lao": 1,
}


# ══════════════════════════════════════════════════════════════════════
#  WHISPER MODEL — lazy-loaded singleton
# ══════════════════════════════════════════════════════════════════════

_WHISPER_MODEL = None
_WHISPER_SIZE = "tiny"   # tiny = real-time capable (~2 s per 3 s chunk on CPU)
                         # base = better accuracy but ~15 s per chunk (not real-time)
                         # small = better Urdu/South Asian accuracy
                         # medium = best accuracy, slow on CPU
_WHISPER_LOCK = threading.Lock()


def _load_whisper():
    """Load Whisper model once, cache forever. Thread-safe."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL
    with _WHISPER_LOCK:
        if _WHISPER_MODEL is not None:
            return _WHISPER_MODEL
        try:
            import whisper
            print(f"[Whisper] Loading '{_WHISPER_SIZE}' model (first time ~10 s)...")
            _WHISPER_MODEL = whisper.load_model(_WHISPER_SIZE)
            print(f"[Whisper] Model ready.")
        except Exception as e:
            print(f"[Whisper] Failed to load: {e}")
            _WHISPER_MODEL = False
    return _WHISPER_MODEL


def set_model_size(size):
    """Change the Whisper model size. Call before first use."""
    global _WHISPER_MODEL, _WHISPER_SIZE
    _WHISPER_SIZE = size
    _WHISPER_MODEL = None   # force reload


# ══════════════════════════════════════════════════════════════════════
#  TRANSCRIPTION
# ══════════════════════════════════════════════════════════════════════

def transcribe_audio(audio, sr=16000):
    """
    Transcribe an audio chunk using Whisper.

    Parameters
    ----------
    audio : numpy array – raw audio samples (mono, float32)
    sr    : int – sample rate

    Returns
    -------
    text         : str – transcribed text (empty if no speech detected)
    confidence   : float – average log-probability (higher = more confident)
    language     : str – detected language code (e.g. "en", "es", "fr")
    """
    model = _load_whisper()
    if model is False or model is None:
        return "", 0.0, "unknown"

    # Whisper expects float32 at 16 kHz
    if sr != 16000:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
    audio = audio.astype(np.float32)

    result = model.transcribe(
        audio,
        language=None,         # auto-detect language
        task="transcribe",
        fp16=False,            # CPU mode
        no_speech_threshold=0.4,
    )

    text = result.get("text", "").strip()
    language = result.get("language", "unknown")

    # Calculate average confidence from segment log-probs
    segments = result.get("segments", [])
    if segments:
        avg_logprob = np.mean([s.get("avg_logprob", -1.0) for s in segments])
        # Convert log-prob to 0-1 scale
        confidence = float(np.exp(avg_logprob))
    else:
        confidence = 0.0

    # Filter out low-confidence transcriptions
    if confidence < TRANSCRIPTION_CONFIDENCE:
        return "", confidence, language

    return text, confidence, language


# ══════════════════════════════════════════════════════════════════════
#  DISTRESS KEYWORD DETECTION
# ══════════════════════════════════════════════════════════════════════

def detect_distress(text):
    """
    Scan transcribed text for distress keywords.

    Parameters
    ----------
    text : str – the transcribed speech

    Returns
    -------
    has_distress : bool – True if any keyword found
    keywords     : list of str – matched keywords
    confidence   : float – how strong the match is (0–1)
    """
    if not text:
        return False, [], 0.0

    text_lower = text.lower()
    found = []

    for keyword in DISTRESS_KEYWORDS:
        if keyword.lower() in text_lower:
            found.append(keyword)

    if not found:
        return False, [], 0.0, 0
    # ── Compute risk score from keyword severity ──
    max_severity = 0
    for kw in found:
        sev = KEYWORD_SEVERITY.get(kw.lower(), 1)
        if sev > max_severity:
            max_severity = sev

    # Confidence based on number and severity of keywords
    base_conf = min(0.5 + len(found) * 0.15, 0.95)

    # Boost for high-severity keywords
    if max_severity >= 3:
        base_conf = min(base_conf + 0.1, 0.98)

    return True, found, base_conf, max_severity


# ══════════════════════════════════════════════════════════════════════
#  MASTER FUNCTION — transcribe + detect distress
# ══════════════════════════════════════════════════════════════════════

def analyse_speech(audio, sr=16000, yamnet_speech_score=0.0):
    """
    Full speech analysis pipeline.

    Only runs Whisper if YAMNet detects some speech presence
    (avoids wasting CPU on pure engine noise).

    Parameters
    ----------
    audio              : numpy array – raw audio
    sr                 : int – sample rate
    yamnet_speech_score: float – YAMNet's confidence that this is speech
                           (0–1). If very low, we skip Whisper entirely.

    Returns
    -------
    dict with keys:
        active        : bool – was speech detected?
        transcript    : str – what was said
        language      : str – detected language
        has_distress  : bool – distress keyword found?
        keywords      : list – matched keywords
        confidence    : float – distress confidence (0–1)
    """
    # Always run Whisper — we need it to detect "help" and other keywords
    # even when YAMNet doesn't classify the audio as speech.
    # Set to 0.0 so the gate never blocks Whisper.
    if yamnet_speech_score < 0.0:
        return {
            "active": False,
            "transcript": "",
            "language": "",
            "has_distress": False,
            "keywords": [],
            "confidence": 0.0,
            "risk_score": 0,
        }

    # ── Transcribe ──────────────────────────────────────────────────
    text, conf, language = transcribe_audio(audio, sr)

    if not text:
        return {
            "active": True,
            "transcript": "",
            "language": language,
            "has_distress": False,
            "keywords": [],
            "confidence": 0.0,
            "risk_score": 0,
        }

    # ── Scan for distress keywords ──────────────────────────────────
    has_distress, keywords, distress_conf, kw_risk = detect_distress(text)

    return {
        "active": True,
        "transcript": text,
        "language": language,
        "has_distress": has_distress,
        "keywords": keywords,
        "confidence": distress_conf,
        "risk_score": kw_risk,
    }
