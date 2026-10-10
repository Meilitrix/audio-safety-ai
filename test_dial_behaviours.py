"""
Dial behaviour log - the eleven scenarios the Danger Dial must pass.

  python test_dial_behaviours.py
  (spare brain:  set BRAIN=http://localhost:5010  set AUDIO_SAFETY_PORT=5010)

Each scenario calls /start_session first, so the brain builds a fresh
DangerScorer and the numbers describe only that scenario.  Audio is real
recordings from sfx_training/ plus chunks cut from your own labelled
journeys; nothing is synthesised except silence.

Measured behaviour on 2026-10-10, after the loudness / words / memory fixes:
  1 benign highway + engine idle ......... dial 0.0 NORMAL   PASS
  2 sustained scream, quiet room ......... voice 2 x6 -> 9.0 HIGH RISK  PASS
  3 same scream INSIDE highway noise ..... identical 9.0 HIGH RISK  PASS
                                          (road noise does NOT suppress it)
  4 scream in bursts (pause between) ..... 6.0 ELEVATED  PASS
                                          (was 1.5 NORMAL: a half-second cry
                                          inside a 3 s chunk used to be diluted
                                          to "quiet" by the 3-second average;
                                          loudness is now the loudest 100 ms)
  5 word_severity=3 on near silence ...... +4.0 then +3.0 -> 7.0 ELEVATED PASS
  6 word + scream over traffic ........... 22.2 CRITICAL in 4 chunks  PASS
  7 quiet glass / slap ................... event never reaches 2  GAP
  8 journey model, chunks YOU labelled ... 95%/97% danger, 25%/32% safe PASS
  9 plain transcript, no severity sent ... 'bachao' 3, repeat 3, 'gaari roko
                                          bhai' 2 -> 9.0 HIGH RISK PASS; "i
                                          cannot believe you know" -> 0 (no
                                          false fire), "theek hai" -> 1, 0 pts
 10 one whispered 'bachao' then 42 s quiet  holds 3.0 CONCERNING the whole time
                                          PASS (used to be erased in ~6 s)
 11 scenario 1 again with the journey model ON ... still 0.0 NORMAL, model read
                                          8% - so leaving it ON by default does
                                          not cost false alarms
"""
import io
import json
import os
import wave

import librosa
import numpy as np
import requests

# Point at a spare brain with:  set BRAIN=http://localhost:5010
# A stale server already holding 5004 will otherwise answer for the new code.
BASE = os.environ.get("BRAIN", "http://localhost:5004")
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
    """chunks: list of (audio, word_severity or None[, transcript or None])"""
    jid = "BH" + title.split()[0].replace("-", "") + "1"
    requests.post(BASE + "/start_session", json={"journey_id": jid}, timeout=30)
    print(f"\n{'=' * 74}\n  {title}\n  {note}\n  expect: {expect}\n{'=' * 74}")
    print("   #  word voice event  chunk  dial   label        sound")
    rows = []
    for i, item in enumerate(chunks):
        y, ws = item[0], item[1]
        tr = item[2] if len(item) > 2 else None
        data = {"journey_id": jid, "chunk_index": str(i)}
        if ws is not None:
            data["word_severity"] = str(ws)
        if tr is not None:
            data["transcript"] = tr
        d = requests.post(BASE + "/upload_chunk",
                          files={"audio": ("c.wav", wav_bytes(y), "audio/wav")},
                          data=data, timeout=180).json()
        r = dict(n=i, word=d.get("word_severity", 0), voice=d.get("voice_severity", 0),
                 event=d.get("event_severity", 0), chunk=d.get("chunk_score", 0),
                 dial=d.get("dial_score", 0), label=d.get("dial_label", "?"),
                 sound=(d.get("sound_name") or "")[:20],
                 etype=d.get("event_type", ""), model=d.get("chunk_model_prob"),
                 peak=d.get("peak"), hold=d.get("distress_hold_chunks"),
                 src=d.get("word_source", ""), kw=d.get("keywords") or [])
        rows.append(r)
        tags = f"  [{r['etype']}]" if r["event"] else ""
        tags += f"  model={r['model']:.0%}" if r["model"] is not None else ""
        tags += f"  hold={r['hold']}" if r["hold"] else ""
        tags += f"  <{','.join(r['kw'])[:22]}({r['src']})>" if r["word"] else ""
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

# Build check: this log is worthless if a stale process answers on this port
# (it happened - the numbers described code that was no longer in the file).
requests.post(BASE + "/start_session", json={"journey_id": "BHBUILD1"}, timeout=30)
_chk = requests.post(BASE + "/upload_chunk",
                     files={"audio": ("c.wav", wav_bytes(SILENCE), "audio/wav")},
                     data={"journey_id": "BHBUILD1", "chunk_index": "0"},
                     timeout=180).json()
if "energy_avg" not in _chk:
    raise SystemExit(f"\n  STOP - the brain on {BASE} is running OLD code "
                     "(no 'energy_avg' in its reply). Kill every server.py "
                     "process and start a fresh one, then re-run this.")
print(f"  [build check] OK - {BASE} is running the current scoring_engine.py")
# Scenarios 1-7 are the acoustic sensors, measured with the journey model OFF so
# they stay comparable to the earlier log.  8 and 11 measure the model.
requests.post(BASE + "/set_model", json={"enabled": False}, timeout=30)
print("  [setup] journey-trained chunk model OFF for scenarios 1-7")

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
         "each cry must read voice=2 and stack, because the memory blocks the "
         "pause chunks from erasing it")

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

# 9 ───────────────────────── words sent as plain text: the brain must decide
#    (a client should never have to judge severity - it only reports words)
quiet3 = tile(quiet_room)
scenario("9-transcript-bachao", [(SILENCE, None, ""),
                                 (quiet3, None, "bachao"),
                                 (quiet3, None, "bachao . bachao mujhe"),
                                 (quiet3, None, "gaari roko bhai"),
                                 (quiet3, None, "i cannot believe you know that"),
                                 (quiet3, None, "theek hai sir")],
         "only a transcript, no loudness, no severity sent - the brain owns the "
         "dictionary; the last two lines are ordinary talk that must not fire",
         "words 3,3,2 then 0,1 - 'cannot/know' must NOT match 'no'/'kill'")

# 10 ───────────────────────────────── how long does one distress word stay felt
hold_tail = [(SILENCE, None, "") for _ in range(14)]
scenario("10-distress-memory",
         [(SILENCE, None, "bachao")] + hold_tail,
         "one whispered 'bachao', then 42 seconds of pure silence",
         "the dial must NOT fall back inside ~60 s (the old code erased it in "
         "two chunks because decay was 1.0 and a voice-only chunk was worth 1.5)")

# 11 ────────────────────────────────── cost of leaving the journey model ON
scenario("11-model-on-benign", [(tile(road), None), (tile(road), None),
                                (tile(idle), None), (tile(idle), None)],
         "the SAME benign highway + engine idle as scenario 1, model ON",
         "false-alarm cost of the new default: how much does normal traffic "
         "score when the trained model is left running")

# ─────────────────────────────────────────────────────────────────── summary
print(f"\n{'=' * 74}\n  SUMMARY\n{'=' * 74}")
print(f"  {'scenario':24s} {'peak':>5} {'final':>7}  {'final label':<12}")
for r in RESULTS:
    print(f"  {r['scenario']:24s} {r['peak']:>5.1f} {r['final_dial']:>7.1f}  {r['final_label']:<12}")
json.dump(RESULTS, open("dial_behaviour_log.json", "w"), indent=1)
print("\n  machine-readable copy -> dial_behaviour_log.json")
