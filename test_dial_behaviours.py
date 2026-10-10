"""
Dial behaviour log - the eight scenarios the Danger Dial must pass.

  python test_dial_behaviours.py

Each scenario calls /start_session first, so the brain builds a fresh
DangerScorer and the numbers describe only that scenario.  Audio is real
recordings from sfx_training/ plus chunks cut from your own labelled
journeys; nothing is synthesised except silence.

Measured behaviour on 2026-10-10 (the numbers this file reproduces):
  1 benign highway + engine idle ......... dial 0.0 NORMAL   PASS
  2 sustained scream, quiet room ......... voice 2 x6 -> 9.0 HIGH RISK  PASS
  3 same scream INSIDE highway noise ..... identical 9.0 HIGH RISK  PASS
                                          (road noise does NOT suppress it)
  4 scream in bursts (pause between) ..... stalls at 1.5 NORMAL  GAP
  5 word_severity=3 on near silence ...... +4.0 then +3.0 -> 7.0 ELEVATED PASS
                                          (words beat the 1.5 voice-only cap)
  6 word + scream over traffic ........... escalates fastest  PASS
  7 quiet glass / slap ................... event never reaches 2  GAP
  8 journey model, chunks YOU labelled ... 95% / 97% on danger, 25% on safe PASS
                                          (catches danger that is NOT loud)
"""
import io
import json
import wave

import librosa
import numpy as np
import requests

BASE = "http://localhost:5004"
SR = 16000
CH = 3 * SR                      # one chunk = 3 seconds

CARS = "sfx_training/car_sounds/"
HIGHWAY = CARS + "455838__kyles__traffic-heavy-dense-wash-highway-gridlock-slowly-advancing-rumble-heard-from-inside-car-with-all-windows-down-montreal-canada.flac"
IDLE = CARS + "car-engine-idling-after-start-vadi-sound-vehicle-car-vw-polo-engine-start-idle-vadi-1-0m43s.mp3"
ROLLER = "sfx_training/scream_sounds/566581__milliistewart15__roller-coaster-screams.mp3"
MALE = "sfx_training/scream_sounds/556976__marc3122__male-screams-1.mp3"
GLASS = "sfx_training/danger_sounds/745291__samsterbirdies__ceramic-clack-glass-hit.flac"
SLAP = "sfx_training/slap_sounds/117347__stereostereo__10-slap_real.aiff"
SILENCE = np.zeros(CH, dtype=np.float32)

RESULTS = []


def load(path, dur=3.0, offset=0.0):
    y, _ = librosa.load(path, sr=SR, mono=True, offset=offset, duration=dur)
    return y.astype(np.float32)


def tile(y, n=CH):
    if len(y) == 0:
        return np.zeros(n, dtype=np.float32)
    return np.tile(y, int(np.ceil(n / len(y))))[:n].astype(np.float32)


def scale(y, target_peak):
    p = float(np.max(np.abs(y))) if len(y) else 0.0
    return y * (target_peak / p) if p > 0 else y


def mix(a, b):
    n = min(len(a), len(b))
    return a[:n] + b[:n]


def wav_bytes(y):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
    return b.getvalue()


def scenario(title, chunks, note, expect):
    """chunks: list of (audio, word_severity or None)"""
    jid = "BH" + title.split()[0].replace("-", "") + "1"
    requests.post(BASE + "/start_session", json={"journey_id": jid}, timeout=30)
    print(f"\n{'=' * 74}\n  {title}\n  {note}\n  expect: {expect}\n{'=' * 74}")
    print("   #  word voice event  chunk  dial   label        sound")
    rows = []
    for i, (y, ws) in enumerate(chunks):
        data = {"journey_id": jid, "chunk_index": str(i)}
        if ws is not None:
            data["word_severity"] = str(ws)
        d = requests.post(BASE + "/upload_chunk",
                          files={"audio": ("c.wav", wav_bytes(y), "audio/wav")},
                          data=data, timeout=180).json()
        r = dict(n=i, word=d.get("word_severity", 0), voice=d.get("voice_severity", 0),
                 event=d.get("event_severity", 0), chunk=d.get("chunk_score", 0),
                 dial=d.get("dial_score", 0), label=d.get("dial_label", "?"),
                 sound=(d.get("sound_name") or "")[:20],
                 etype=d.get("event_type", ""), model=d.get("chunk_model_prob"))
        rows.append(r)
        tags = f"  [{r['etype']}]" if r["event"] else ""
        tags += f"  model={r['model']:.0%}" if r["model"] is not None else ""
        print(f"  {i:>2}  {r['word']:>4} {r['voice']:>5} {r['event']:>5} "
              f"{r['chunk']:>6} {r['dial']:>6.1f}  {r['label']:<12} {r['sound']}{tags}")
    peak = max([r["dial"] for r in rows] or [0.0])
    top = max(rows, key=lambda r: r["dial"])["label"] if rows else "?"
    print(f"   => peak {peak:.1f}  ({top})")
    RESULTS.append(dict(scenario=title, peak=peak, final_label=rows[-1]["label"] if rows else "?",
                        final_dial=rows[-1]["dial"] if rows else 0.0, verdict=expect, rows=rows))


print("Danger Dial behaviour log")
print(f"brain: {BASE}")
requests.get(BASE + "/", timeout=15)

# 1 ──────────────────────────────────────────────────────────── benign noise
road = scale(load(HIGHWAY, 12.0, 2.0), 0.60)
idle = scale(load(IDLE, 12.0, 3.0), 0.55)
scenario("1-benign-traffic", [(tile(road), None), (tile(road), None),
                              (tile(idle), None), (tile(idle), None)],
         "heavy highway gridlock + engine idle, loud (peak 0.55-0.60)",
         "dial stays 0.0 NORMAL - no false alarm on a normal ride")

# 2-3 ───────────────────────────────────────────── scream, alone and in traffic
loud_roller = [tile(scale(load(ROLLER, 3.0, t), 0.92)) for t in (0, 3, 6, 9, 12, 15)]
scream18 = scale(load(ROLLER, 18.0, 0.0), 0.92)
road18 = scale(load(HIGHWAY, 18.0, 2.0), 0.55)
in_traffic = [tile(mix(scream18, road18)[i * CH:(i + 1) * CH]) for i in range(6)]

scenario("2-scream-quiet-room", [(c, None) for c in loud_roller],
         "sustained roller-coaster scream, 18 s, no traffic",
         "voice=2 every chunk, +1.5 each -> HIGH RISK by chunk 5")
scenario("3-scream-in-traffic", [(c, None) for c in in_traffic],
         "THE SAME scream mixed over highway rumble (only variable = road noise)",
         "identical climb if road noise does not suppress the loudness sensor")

# 4 ──────────────────────────────────────────────── distress in bursts (the gap)
bursts = [tile(scale(load(MALE, 3.0, t % 9.0), 0.90)) for t in range(8)]
alternating = [(bursts[i], None) if i % 2 == 0 else (SILENCE, None) for i in range(8)]
scenario("4-distress-in-bursts", alternating,
         "a cry-out, then a pause, then a cry-out - how a real victim often sounds",
         "should still escalate; known gap if the silence chunks zero the score")

# 5-6 ────────────────────────────────────────────────────── the keyword sensor
quiet_room = scale(load(IDLE, 3.0, 5.0), 0.10)
scenario("5-words-only", [(SILENCE, None), (quiet_room, 3), (SILENCE, 3),
                          (SILENCE, None), (SILENCE, None)],
         "near-silence with word_severity=3 (a whispered 'bachao') - no loudness",
         "words alone must beat the 1.5 voice-only cap")
scenario("6-words-in-traffic", [(tile(mix(scream18[:CH], road18[:CH])), 3),
                                (tile(mix(scream18[CH:2 * CH], road18[CH:2 * CH])), 3),
                                (tile(mix(scream18[2 * CH:3 * CH], road18[2 * CH:3 * CH])), 2),
                                (tile(mix(scream18[3 * CH:4 * CH], road18[3 * CH:4 * CH])), 2)],
         "shouted 'bachao' over highway: word + voice + road noise together",
         "fastest escalation of any scenario")

# 7 ─────────────────────────────────────────────── impact events at low volume
scenario("7-quiet-impacts",
         [(tile(scale(load(GLASS, 3.0, 0.0), 0.30)), None) for _ in range(3)] +
         [(tile(scale(load(SLAP, 3.0, 0.0), 0.30)), None) for _ in range(3)],
         "glass hit and slap scaled to peak 0.30 (below the scream gate)",
         "event_pts=2 only if YAMNet's top label is in a danger set")

# 8 ───────────────────────────── the journey model on chunks YOU labelled by hand
requests.post(BASE + "/set_model", json={"enabled": True}, timeout=30)
print("\n  [setup] journey-trained chunk model -> ON")
lab = json.load(open("saved_journeys/20261008123835.label.json", encoding="utf-8"))
dg_idx = [c["index"] for c in lab.get("chunks", []) if c.get("label") == "danger"]
danger_chunks = [tile(load("saved_journeys/20261008123835.wav", 3.0, i * 3.0)) for i in dg_idx[:2]]
safe_chunks = [tile(load("saved_journeys/20261008144747.wav", 3.0, i * 3.0)) for i in (1, 2)]
scenario("8-journey-model", [(c, None) for c in danger_chunks + safe_chunks],
         f"chunks {dg_idx[:2]} are ones you marked DANGER; the last two are from a "
         "journey you marked SAFE - all at whatever volume they really were",
         "P(danger) high on your danger chunks, low on safe - and it must score "
         "even when voice=0")
requests.post(BASE + "/set_model", json={"enabled": False}, timeout=30)
print("  [setup] journey-trained chunk model -> back OFF (server default)")

# ─────────────────────────────────────────────────────────────────── summary
print(f"\n{'=' * 74}\n  SUMMARY\n{'=' * 74}")
print(f"  {'scenario':24s} {'peak':>5} {'final':>7}  {'final label':<12}")
for r in RESULTS:
    print(f"  {r['scenario']:24s} {r['peak']:>5.1f} {r['final_dial']:>7.1f}  {r['final_label']:<12}")
json.dump(RESULTS, open("dial_behaviour_log.json", "w"), indent=1)
print("\n  machine-readable copy -> dial_behaviour_log.json")
