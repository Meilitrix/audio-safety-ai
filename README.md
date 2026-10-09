# Audio Safety AI — Ride-Sharing Safety Monitor

An AI system that **listens to sounds inside a car** in real-time, classifies them as **SAFE** or **DANGER**, and displays a live risk gauge. Built for ride-sharing safety monitoring.

---

## What Does This System Do?

```
┌──────────────┐     ┌────────────────────┐     ┌──────────────────┐
│  BROWSER MIC │ ──▶ │  YAMNet (521 class │ ──▶ │  RISK GAUGE +    │
│  (live audio)│     │  audio classifier) │     │  LIVE TRANSCRIPT │
└──────────────┘     │                    │     └──────────────────┘
                     │  + Energy analysis │
                     │  + Pitch analysis  │
                     │  + Web Speech API  │
                     └────────────────────┘
```

1. **Listens** to live audio from your browser microphone
2. **Classifies** every 3-second chunk using Google YAMNet (recognises 521 sound types)
3. **Transcribes** speech in real-time using the Web Speech API (browser-native)
4. **Detects** screams, shouts, crashes, sudden silence, and distress keywords
5. **Displays** a live risk gauge (levels 0–4), chunk analysis, and timestamped transcription
6. **Records** the full journey as a single WAV file for playback or later review

---

## Architecture

| Component | Technology | Where It Runs |
|---|---|---|
| Sound classification | Google YAMNet (TensorFlow Hub) | Server (Python) |
| Custom danger classifier | SVM / Random Forest / KNN, cross-validated (`train_model/`) | Server (Python) |
| Speech transcription | Web Speech API | Browser (JavaScript) |
| Energy analysis | Custom (numpy) | Server (Python) |
| Pitch analysis | librosa pyIN | Server (Python) |
| Danger Dial score | Temporal accumulation + decay (`scoring_engine.py`) | Server (Python) |
| Risk gauge | Rolling buffer (5 chunks) | Server + Frontend |
| Distress keywords | 145+ keywords (EN/UR/HI/PA/PS) | Browser (JavaScript) |
| Backend | Flask (threaded) | Server (Python) |
| Frontend | Native HTML/CSS/JS | Browser |

---

## Project Structure

```
audio-safety-ai/
│
├── server.py              ★ ENTRY POINT — Flask backend: serves the frontend,
│                           receives 3-sec chunks, runs both classifiers,
│                           scores the danger dial, manages journeys
├── index.html             Self-contained frontend — gauge, transcription,
│                           chunk analysis, waveform, timers, journey archive
│
├── yamnet_engine.py       AI layer 1 — YAMNet classification + energy + pitch
│                           analysis → SAFE or DANGER
├── yamnet_classes.py      521 embedded YAMNet class names (AudioSet)
├── scoring_engine.py      AI layer 4 — Danger Dial: temporal accumulation,
│                           repetition / escalation / combination bonuses, decay
│
├── config.py              Settings for the LEGACY pipeline only (not read by
│                           server.py — see legacy_cli/ below)
│
├── train_model/           Custom danger classifier (AI layer 1b)
│   ├── audio_features.py    16 kHz / 13 MFCC + energy, pitch, spectral stats
│   ├── train_classifier.py  Trains SVM / RF / GB / KNN on sfx_training/
│   ├── predictor.py         DangerPredictor — loads the best .pkl for server.py
│   └── models/              Trained .pkl output (git-ignored)
├── sfx_training/          Training audio, one folder per class
│   ├── car_sounds/          → label SAFE   (engine, traffic, road noise)
│   └── danger_sounds/  scream_sounds/  slap_sounds/   → label DANGER
│
├── test_mic.py            Diagnostic — tests mic + YAMNet from the terminal
├── test_scenarios.py        Replay 12 scenario families through DangerScorer
├── analyze_car_sounds.py    Audit car recordings chunk-by-chunk (YAMNet only)
├── full_audio_audit.py      Audit ALL sfx_training files (YAMNet + dial)
│
├── legacy_cli/            ⚠️ RETIRED first-generation pipeline (not used by
│   ├── main.py              server.py).  Run with `python -m legacy_cli.main`
│   ├── config imports …     Random Forest on 20 MFCC @ 22 050 Hz, synthetic
│   └── alert_system.py      training data, local mic monitor, webhook alerts
│
├── presentation.html      Hackathon walkthrough
├── requirements.txt       Python dependencies
│
├── saved_journeys/        Recorded journey WAV files (created at runtime)
└── _audio_chunks/         Temporary 3-sec chunks (created at runtime)
```

**Two audio feature extractors exist and are not interchangeable:**
`train_model/audio_features.py` (16 kHz, 13 MFCC — used by the live app) and
`legacy_cli/feature_extractor.py` (22 050 Hz, 20 MFCC — retired).  They are
namespaced as separate packages precisely so a model trained by one can never
be scored by the other by accident.

---

## Quick Start

### Prerequisites

- **Python 3.10+** installed
- A working **microphone**
- **Chrome or Edge** browser (required for Web Speech API)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/Meilitrix/audio-safety-ai.git
cd audio-safety-ai

# 2. Install dependencies
pip install -r requirements.txt
```

### Optional — train the custom classifier

The app runs on YAMNet alone. Training the second classifier improves detection
of slaps, impacts and screams that YAMNet misses:

```powershell
python -m train_model.train_classifier
# compares SVM (RBF/Linear), Random Forest, KNN by cross-validation,
# then writes train_model/models/danger_classifier_latest.pkl
```

If the `.pkl` is absent, `server.py` prints
*"Custom classifier not available"* and simply runs YAMNet-only — it is a
degrade, not an error.

### Run

```bash
# Set environment variable to suppress TensorFlow warnings (Windows)
$env:TF_CPP_MIN_LOG_LEVEL="3"

# Start the server
python server.py
```

Open **http://localhost:5004** in Chrome or Edge.

---

## How to Use

### Start Monitoring (AI Analysis + Transcription)

1. Click **START MONITOR**
2. Allow microphone access when the browser asks
3. The AI analyses every 3-second audio chunk:
   - **Gauge** (left) shows current risk level (0 = Normal → 4 = Critical)
   - **Chunk Analysis** (right) shows per-chunk SAFE/DANGER readings
   - **Transcription window** shows live speech-to-text with distress keyword tags
   - **Waveform** displays real-time audio visualization

### Start Recording (Journey Save)

1. Click **START RECORDING** to begin saving audio
2. Click **STOP RECORDING** to save the journey as a single WAV file
3. Recorded journeys appear in the **Journey Audio Archive** at the bottom

### Monitoring and Recording are Independent

- You can monitor without recording (AI analysis only)
- You can record without monitoring (raw audio capture only)
- Both can run simultaneously

---

## Detection Layers

### Layer 1: YAMNet Sound Classification
Google's pre-trained model recognises 521 sound types from the AudioSet dataset. Only these trigger DANGER:

| Class | Description |
|---|---|
| Scream (386) | High-pitched vocal distress |
| Shriek (387) | Sharp piercing vocalisation |
| Shout (10) | Aggressive raised voice |
| Yell (13) | Loud vocal outcry |
| Crash (393) | Physical impact sound |
| Collapse (394) | Structural falling sound |

Everything else (speech, traffic, music, engine, horns) → SAFE.
DANGER needs ≥ 50 % YAMNet confidence (`DANGER_THRESHOLD` in `yamnet_engine.py`).

### Layer 1b: Custom Danger Classifier (optional, `train_model/`)
A scikit-learn model — cross-validated across SVM (RBF), SVM (linear), Random
Forest and KNN, best scorer wins — trained on `sfx_training/`: car sounds
labelled SAFE; danger, scream and slap sounds labelled DANGER.  Features are
16 kHz MFCC + energy + pitch + spectral (`train_model/audio_features.py`).
It runs on every chunk and, if it reports DANGER above 70 % confidence where
YAMNet said SAFE, it **overrides** the YAMNet verdict (`server.py`,
`_get_custom_predictor`).  Without the trained `.pkl` this layer is skipped
automatically.

⚠️ The current corpus is tiny (14 decodable clips, 4 SAFE / 10 DANGER), so the
reported cross-validation accuracy is indicative only, not a reliability claim.
One `.m4a` clip is skipped because libsndfile cannot decode it.

### Layer 2: Energy Analysis
- **Sudden silence** — detects when audio energy drops sharply (possible vehicle stop)
- **Loud burst** — detects sudden energy spikes

### Layer 3: Pitch Analysis
- Estimates fundamental frequency (F0) using librosa
- Normal speech: 85–255 Hz
- Screaming: 400–1500+ Hz

### Layer 4: Speech Transcription (Browser)
- Web Speech API transcribes speech in real-time
- Scans for 145+ distress keywords in English, Urdu, Hindi, Punjabi, and Pashto
- Keywords highlighted in red tags in the transcription window

### Layer 5: Danger Dial (`scoring_engine.py`)
A running score rather than a per-chunk verdict, so escalation and repetition
count even when no single chunk is alarming:

```
score = previous + word signal + voice signal + event signal
              + repetition bonus + escalation bonus + combination bonus
              - decay
```

Decay only kicks in after ~8 chunks of normal audio, so one momentary spike
doesn't move the dial much but sustained pressure does.

---

## Distress Keywords (Multilingual)

| Language | Examples |
|---|---|
| English | help, stop, no, let me go, I'm scared |
| Urdu (Roman) | bachao, madad, ruko, mujhe chhod do, police bulao |
| Urdu (Script) | بچاؤ, مدد, رکو, نہیں, مجھے چھوڑو |
| Punjabi | bacha lao, madad karo, menu chhod do |
| Pashto | madad, wadre, police |

---

## Risk Gauge and Danger Dial

The UI shows **two** independent readings — don't conflate them:

### Danger Dial (accumulated score from `scoring_engine.py`)

| Score | Label |
|---|---|
| 0 | NORMAL |
| 1–2 | CONCERNING |
| 3–4 | ELEVATED |
| 5–7 | HIGH RISK |
| 8+ | CRITICAL |

### Chunk Risk Gauge (0–4)

| Level | Name | Meaning |
|---|---|---|
| 0 | NORMAL | All signals safe |
| 1 | CONCERNING | Minor anomaly detected |
| 2 | ELEVATED | Multiple signals active |
| 3 | HIGH RISK | Strong danger indicators |
| 4 | CRITICAL | Sustained distress detected |

Computed per chunk from YAMNet verdict + confidence, keyword risk, pitch
(screaming) and silence signals, then averaged over a rolling buffer of the
last 5 chunks to smooth out momentary spikes.

### SAFE/DANGER verdict

Separately, a 3-chunk smoothing buffer requires **2 consecutive DANGER chunks**
(~4–6 s) *and* ≥ 80 % confidence before `status` flips to DANGER
(`_smooth_stable` in `server.py`).  This is the anti-false-positive layer.

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/` | Serve the frontend |
| POST | `/start_session` | Begin a monitoring session (fresh scorer, cleared buffers) |
| POST | `/toggle_recording` | Opt in / out of saving audio while monitoring continues |
| POST | `/stop_session` | End session; combine chunks into a journey **only if recording was on** |
| POST | `/upload_chunk` | Receive 3-sec WAV, run both classifiers + dial, return result |
| GET | `/journeys` | List saved journey files |
| GET | `/saved_journeys/<name>` | Serve a journey WAV for playback |
| DELETE | `/journeys/<name>` | Delete a specific journey |
| POST | `/delete_all_journeys` | Delete all saved journeys + pending chunks |

---

## Other Scripts

| Script | Purpose |
|---|---|
| `test_mic.py` | Terminal diagnostic: mic detection, energy readout, live YAMNet monitoring |
| `test_scenarios.py` | Replays 12 scenario families through `DangerScorer` — no mic needed |
| `analyze_car_sounds.py` | Runs YAMNet chunk-by-chunk over `sfx_training/car_sounds/` |
| `full_audio_audit.py` | Runs every `sfx_training/` file through YAMNet + the danger dial |

```bash
$env:TF_CPP_MIN_LOG_LEVEL="3"
python test_mic.py            # live mic
python test_scenarios.py      # scoring engine only
```

---

## Legacy Pipeline (`legacy_cli/`)

⚠️ **Not used by `server.py`.**  This is the first generation of the project: a
terminal menu that generates synthetic audio, trains a Random Forest on 20 MFCC
features at 22 050 Hz, monitors the microphone locally, and POSTs alerts to a
webhook.  It lives in its own package so its `feature_extractor.py` can never be
confused with `train_model/audio_features.py`.

```powershell
python -m legacy_cli.main
```

Requires `data_generator.py` to create a `data/` corpus first (not committed).
`ALERT_ENABLED` defaults to **False** in `config.py`, and `alert_system.py`
refuses to send while `ALERT_WEBHOOK_URL` is still the placeholder value.

---

## Troubleshooting

**"Speech recognition not supported"**
→ Use Chrome or Edge. Firefox/Safari don't support Web Speech API.

**Microphone not working**
→ Check browser permissions. On Windows: Settings → Privacy → Microphone → allow browser.

**"No module named 'tensorflow'"**
→ Run `pip install -r requirements.txt`

**YAMNet loading slowly on first run**
→ Normal — downloads the model (~30 seconds). Cached after first load.

**"Custom classifier not available — run train_model/train_classifier.py first"**
→ Expected if `train_model/models/danger_classifier_latest.pkl` doesn't exist
yet. The app still works on YAMNet alone; run
`python -m train_model.train_classifier` and restart to enable layer 1b.

**Transcription not appearing**
→ Make sure you're speaking loud enough. The browser mic signal can be quiet — the system amplifies audio automatically, but very quiet input may not transcribe.

---

## Tech Stack

- **Backend:** Python, Flask, TensorFlow, TensorFlow Hub, librosa, numpy, scikit-learn
- **Frontend:** Native HTML5, CSS3, JavaScript (no frameworks)
- **AI Models:** Google YAMNet (521-class audio), custom scikit-learn classifier, Web Speech API (transcription)
- **Audio Capture:** ScriptProcessorNode (raw PCM), browser microphone

---

## License

This project is for educational and development purposes.
