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
| Speech transcription | Web Speech API | Browser (JavaScript) |
| Energy analysis | Custom (numpy) | Server (Python) |
| Pitch analysis | librosa pyIN | Server (Python) |
| Risk gauge | Rolling buffer (5 chunks) | Server + Frontend |
| Distress keywords | 100+ keywords (EN/UR/HI/PA/PS) | Browser (JavaScript) |
| Backend | Flask (threaded) | Server (Python) |
| Frontend | Native HTML/CSS/JS | Browser |

---

## Project Structure

```
audio_safety_ai/
│
├── server.py              Flask backend — serves frontend, handles chunk
│                           upload, classification, journey management
│
├── index.html             Self-contained frontend — gauge, transcription,
│                           chunk analysis, waveform, timers, journey archive
│
├── yamnet_engine.py       AI brain — YAMNet classification + energy + pitch
│                           analysis + signal fusion → SAFE or DANGER
│
├── yamnet_classes.py      521 embedded YAMNet class names (AudioSet)
│
├── test_mic.py            Diagnostic tool — tests mic and YAMNet
│                           from the terminal
│
├── requirements.txt       Python dependencies
│
├── config.py              Original pipeline config (legacy)
├── detector.py            Original mic detector (legacy)
├── data_generator.py      Synthetic data generator (legacy)
├── feature_extractor.py   MFCC extractor (legacy)
├── model.py               Random Forest trainer (legacy)
├── alert_system.py        Webhook alert system (legacy)
├── main.py                Original CLI menu (legacy)
│
├── saved_journeys/        Recorded journey WAV files (created at runtime)
└── _audio_chunks/         Temporary 3-sec chunks (created at runtime)
```

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
cd audio_safety_ai

# 2. Install dependencies
pip install -r requirements.txt
```

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

### Layer 2: Energy Analysis
- **Sudden silence** — detects when audio energy drops sharply (possible vehicle stop)
- **Loud burst** — detects sudden energy spikes

### Layer 3: Pitch Analysis
- Estimates fundamental frequency (F0) using librosa
- Normal speech: 85–255 Hz
- Screaming: 400–1500+ Hz

### Layer 4: Speech Transcription (Browser)
- Web Speech API transcribes speech in real-time
- Scans for 100+ distress keywords in English, Urdu, Hindi, Punjabi, and Pashto
- Keywords highlighted in red tags in the transcription window

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

## Risk Gauge Levels

| Level | Name | Meaning |
|---|---|---|
| 0 | NORMAL | All signals safe |
| 1 | CONCERNING | Minor anomaly detected |
| 2 | ELEVATED | Multiple signals active |
| 3 | HIGH RISK | Strong danger indicators |
| 4 | CRITICAL | Sustained distress detected |

The gauge uses a rolling buffer of the last 5 chunks to smooth out momentary spikes.

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/` | Serve the frontend |
| POST | `/upload_chunk` | Receive 3-sec WAV, classify, return result |
| POST | `/start_session` | Begin a monitoring session |
| POST | `/stop_session` | End session, combine chunks into journey |
| GET | `/journeys` | List saved journey files |
| GET | `/saved_journeys/<name>` | Serve a journey WAV for playback |
| DELETE | `/journeys/<name>` | Delete a specific journey |
| POST | `/delete_all_journeys` | Delete all saved journeys |

---

## Diagnostic Tool

Test your microphone and AI pipeline from the terminal:

```bash
$env:TF_CPP_MIN_LOG_LEVEL="3"
python test_mic.py
```

This will:
1. Detect your microphone
2. Record a test sample and show energy levels
3. Run YAMNet classification
4. Start live monitoring (speak, then try screaming or saying "help")

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

**Transcription not appearing**
→ Make sure you're speaking loud enough. The browser mic signal can be quiet — the system amplifies audio automatically, but very quiet input may not transcribe.

---

## Tech Stack

- **Backend:** Python, Flask, TensorFlow, TensorFlow Hub, librosa, numpy
- **Frontend:** Native HTML5, CSS3, JavaScript (no frameworks)
- **AI Models:** Google YAMNet (audio classification), Web Speech API (transcription)
- **Audio Capture:** ScriptProcessorNode (raw PCM), browser microphone

---

## License

This project is for educational and development purposes.
