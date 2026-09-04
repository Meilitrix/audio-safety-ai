# 🚗 Audio Safety AI — Ride-Sharing Safety System

An AI system that **listens to sounds inside a car**, classifies them as **SAFE** or **DANGER**, and **sends an alert to an emergency centre** when danger is detected.

---

## 📖 What Does This System Do?

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────────┐
│  MICROPHONE │ ──▶ │ EXTRACT      │ ──▶ │ AI MODEL      │ ──▶ │ ALERT SYSTEM     │
│  (listens)  │     │ MFCC FEATURES│     │ SAFE or DANGER│     │ → Emergency Ctr  │
└─────────────┘     └──────────────┘     └───────────────┘     └──────────────────┘
```

1. **Listens** to 3-second audio clips from a microphone
2. **Extracts** audio fingerprints (MFCCs — like a musical chord chart)
3. **Classifies** the sound using a trained AI model
4. **Alerts** the emergency centre if danger is detected

---

## 📁 Project Structure — What Each File Does

```
audio_safety_ai/
│
├── config.py              ⚙️  "Control panel" — all settings in one place
│                           (sample rate, file paths, alert URL, etc.)
│
├── data_generator.py      🔊 Creates FAKE training data
│                           Safe = engine hums + calm tones
│                           Danger = shouting + crashes + screams
│
├── feature_extractor.py   🎵 Converts audio into numbers (MFCCs)
│                           that the AI model can understand
│
├── model.py               🧠 The brain — trains a Random Forest
│                           classifier and saves it to disk
│
├── alert_system.py        🚨 Sends emergency alerts (HTTP webhook)
│                           when danger is detected
│
├── detector.py            🎤 Listens through your microphone in
│                           real-time and calls the AI on each clip
│
├── main.py                🎯 THE FILE YOU RUN — gives you a menu
│                           to do everything step by step
│
├── requirements.txt       📦 List of Python packages to install
│
├── data/
│   ├── safe_sounds/       📂 Folder for safe audio clips (generated)
│   └── danger_sounds/     📂 Folder for danger audio clips (generated)
│
└── models/
    └── safety_classifier.pkl  💾 The trained model (saved after training)
```

---

## 🚀 Step-by-Step Guide — How to Run This on Your Computer

### Prerequisites

- **Python 3.8 or newer** installed ([download here](https://www.python.org/downloads/))
- A working **microphone** on your computer
- An internet connection (to install packages)

---

### Step 1: Open a Terminal

**Windows:**
- Press `Win + R`, type `cmd`, press Enter
- Or search for "PowerShell" in the Start menu

**Mac:**
- Press `Cmd + Space`, type `terminal`, press Enter

---

### Step 2: Navigate to the Project Folder

```bash
cd path/to/audio_safety_ai
```

Replace `path/to/` with the actual location of the `audio_safety_ai` folder on your computer.

**Example (Windows):**
```bash
cd C:\Users\YourName\Documents\audio_safety_ai
```

**Example (Mac/Linux):**
```bash
cd ~/Documents/audio_safety_ai
```

---

### Step 3: Create a Virtual Environment (Recommended)

A virtual environment keeps this project's packages separate from your other projects.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal prompt. This means the virtual environment is active.

---

### Step 4: Install the Required Packages

```bash
pip install -r requirements.txt
```

This installs all the libraries the project needs:
- `numpy` — math operations
- `scikit-learn` — the machine learning library (trains the AI)
- `librosa` — audio processing (extracts MFCCs)
- `sounddevice` — records from your microphone
- `soundfile` — saves audio as .wav files
- `requests` — sends HTTP alerts to the emergency centre
- `joblib` — saves/loads the trained model

This might take 2-5 minutes depending on your internet speed.

---

### Step 5: Run the Application

```bash
python main.py
```

You'll see a menu:

```
============================================================
  🚗  AUDIO SAFETY AI — Ride-Sharing Safety System
============================================================

  [1] Generate synthetic training data
  [2] Train the AI model
  [3] Test on a single audio file
  [4] Start real-time safety monitor
  [5] Run full pipeline (generate → train → monitor)
  [0] Quit
```

---

### Step 6: Follow the Menu

#### First time? Use option [5] — it does everything automatically:

1. **Generates** 100 fake audio clips (50 safe + 50 danger)
2. **Trains** the AI model on those clips
3. **Starts** listening through your microphone

#### Or do it step by step:

**Option [1] — Generate Data:**
Creates synthetic audio clips so the AI has something to learn from.
- Safe sounds = low rumbles + soft tones (engine, radio, calm talk)
- Danger sounds = loud bursts + sharp spikes (shouting, crashes)

**Option [2] — Train the Model:**
Teaches the AI to tell safe from danger.
- Loads all audio clips
- Extracts MFCC features (audio fingerprints)
- Trains a Random Forest classifier
- Shows you accuracy on a test set
- Saves the model to `models/safety_classifier.pkl`

**Option [3] — Test a Single File:**
Point the AI at any `.wav` file and see what it thinks.

**Option [4] — Start Live Monitor:**
The AI starts listening through your microphone every 3 seconds.
- If it hears something safe → prints "✅ SAFE"
- If it hears danger → prints "🚨 DANGER" and sends an alert

---

## ⚙️ Configuration

Open `config.py` to change settings:

| Setting | Default | What It Does |
|---------|---------|-------------|
| `AUDIO_DURATION` | 3 | Seconds per audio clip |
| `N_MFCC` | 20 | Number of audio features to extract |
| `N_SAMPLES_PER_CLASS` | 50 | How many fake clips to generate per category |
| `CONFIDENCE_THRESHOLD` | 0.6 | Minimum confidence to trigger alert (0.0–1.0) |
| `ALERT_WEBHOOK_URL` | (placeholder) | URL of your emergency centre's API |
| `ALERT_ENABLED` | True | Set `False` for demo mode (no real HTTP requests) |
| `CONTINUOUS_ALERT_SECONDS` | 5 | Cooldown between repeated alerts |

---

## 🚨 How the Alert System Works

When danger is detected:

1. The AI sends an **HTTP POST request** to your emergency centre's webhook URL
2. The payload looks like this:

```json
{
  "event": "DANGER_DETECTED",
  "timestamp": "2026-09-03T14:30:00.000000",
  "confidence": 0.87,
  "severity": "HIGH",
  "details": {
    "description": "Dangerous sound detected in vehicle",
    "audio_type": "aggressive_shouting_or_crash"
  }
}
```

3. The alert has a **cooldown** (default 5 seconds) to prevent spam
4. If `ALERT_ENABLED = False`, alerts are logged but NOT sent (demo mode)

**To connect to a real emergency centre:**
- Replace `ALERT_WEBHOOK_URL` in `config.py` with the actual API endpoint
- Set `ALERT_ENABLED = True`

---

## 🧪 Testing Without Real Data

The synthetic data generator creates audio that is *structurally different* between safe and danger:
- **Safe** = low frequencies, smooth waves, quiet
- **Danger** = high frequencies, sharp spikes, loud

This means the model will show **high accuracy on synthetic data** because the patterns are distinct. For production use, you'd replace the synthetic data with real recordings.

---

## 🔄 How to Use Your Own Real Audio Data

1. Collect `.wav` files of real car sounds
2. Place safe clips in `data/safe_sounds/`
3. Place danger clips in `data/danger_sounds/`
4. Re-run training (option [2])

The system automatically picks up all `.wav` files in those folders.

---

## ❓ Troubleshooting

**"No module named 'librosa'"**
→ Make sure you ran `pip install -r requirements.txt`

**"No model found" error**
→ You need to train the model first (option [1] then [2], or just [5])

**Microphone not working**
→ Check that your OS allows Python to access the microphone
→ On Windows: Settings → Privacy → Microphone → allow Python

**"Could not connect to webhook URL"**
→ This is normal if you haven't set up a real emergency centre endpoint
→ Set `ALERT_ENABLED = False` in `config.py` for demo mode

---

## 📚 Key Concepts Explained Simply

**MFCC (Mel-Frequency Cepstral Coefficients):**
Think of it like a fingerprint for sound. Just as your fingerprint uniquely identifies you, MFCCs uniquely characterise a sound. The AI compares fingerprints to decide if a sound is safe or dangerous.

**Random Forest:**
A collection of 100 simple decision trees. Each tree votes on whether a sound is safe or danger. The majority wins. It's like asking 100 people and going with the most popular answer.

**Webhook:**
A URL that your emergency centre provides. When we send an HTTP POST request to that URL, their system receives the alert automatically.

---

## 📝 License

This project is for educational and development purposes.
For production deployment in a ride-sharing application, additional considerations include:
- Real-world data collection and labelling
- Model robustness testing
- Latency optimisation
- Redundancy and fail-safes
- Legal and privacy compliance
