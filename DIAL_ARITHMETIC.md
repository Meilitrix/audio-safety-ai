# The Danger Dial — how the number is calculated

This is the arithmetic behind the dial in the Audio Safety AI app. It is written
down so that in six months you can read one page and know exactly why the dial
did what it did, instead of guessing.

Everything here describes the code in `scoring_engine.py` (the rules),
`server.py` (the sensors) and `distress_keywords.json` (the word list).
If the numbers in this file and the numbers in the code ever disagree,
**the code is right and this document is out of date.**

---

## 1. What the dial actually is

The dial is one number, called `accumulated_score`, that the app recalculates
every 3 seconds (one "chunk"). It starts at 0 for each journey and changes like
this:

```
new dial  =  old dial  +  points from this chunk  -  decay
```

Points are added for evidence, taken away slowly when nothing happens, and the
number is never allowed below 0. The number is then mapped to a word:

| dial score | label | colour | meaning |
|---|---|---|---|
| 0 – 1.9 | NORMAL | grey-green | nothing of interest |
| 2 – 4.9 | CONCERNING | lime | one weak signal |
| 5 – 8.9 | ELEVATED | yellow | more than one signal, or a real one |
| 9 – 12.9 | HIGH RISK | orange | strong evidence |
| 13 and above | CRITICAL | red | this is an emergency |

The scale is **not** 1–10. A single chunk can add at most about 8 points, and
measured journeys have reached **22.2**. Ten is a serious reading, but the
dial can go well past it.

---

## 2. The four sensors, and what each one is worth

Each chunk is judged by four independent sensors. They do not know about each
other.

| sensor | what it listens for | points | can it reach 2? |
|---|---|---|---|
| **words** | what was *said* (`distress_keywords.json`) | level 1 = 0.5, level 2 = 1.5, level 3 = **3.0** | yes, 3.0 |
| **voice** | how it was *said* — loudness and pitch | quiet = 0.5, scream = **1.5** | yes, 1.5 |
| **event** | a *sound object* — glass, slap, gunshot, scream | quiet = 0.5, loud = **1.5** | yes, 1.5 |
| **model** | your own trained journey model | 0 to 2.0 (`confidence × 2`) | yes, 2.0 |

### words — the dictionary, not an opinion
A phrase scores only if the spoken words reached the app as text. Levels:

* **level 3** — direct distress: `bachao`, `madad`, `help`, `police`, `emergency`,
  `bachaao`, `meri madad`, `mdad`
* **level 2** — commands, abuse, fear: `gaadi roko`, `ruko`, `chhod de`,
  `khatra`, `danger`, `badameez`, `besharam`, `chup`, `niche utaro`
* **level 1** — could be ordinary conversation: `mar`, `kat`, `piit`, `dar`,
  `bhag`, `uth`, `dekho`, `kaanh`, `niche`, `upar`

The whole point of level 1 is that it is *cheap*: one level-1 word is worth
half a point and on its own cannot move the dial, because a single weak signal
gets cleared to zero (see section 4).

### voice — loudness, measured honestly
"Energy" means the power of the **loudest 100 milliseconds** in the chunk, not
the average of all 3 seconds. That matters: a cry for help lasts half a second,
and averaging it against 2.5 seconds of road noise made it look like a whisper.

| loudest-100 ms energy | roughly what it is | voice severity |
|---|---|---|
| above 0.045 | about 0.85 peak volume | **2** (scream) |
| above 0.0015 | about 0.15 peak volume | 1 |
| below | silence | 0 |

Pitch: if the human-frequency band dominates the spectrum, that's a 2.

### event — recognised sounds, and the levels they need
| sound | needs | weak hit | strong hit |
|---|---|---|---|
| Gun_shot, Firearms | 0.30 | 0.10 → 1 | 2 |
| Glass (breaking) | 0.35 | 0.10 → 1 | 2 |
| Slap, beating | 0.35 | 0.12 → 1 | 2 |
| thump, knock (dull impact) | 0.40 | 0.12 → 1 | 2 |
| scream, shout, yell | 0.30 | 0.12 → 1 | 2 |

Car engine, horn, tire noise and traffic are deliberately worth **0**. This is
why heavy road noise no longer pushes the dial up.

### model — the trained sensor
This is the only sensor that comes from your labelled recordings, and the only
one that can help when a danger is **quiet**. It is switched on with the
"Trained danger model" toggle and needs at least 2 safe + 2 danger labelled
chunks before it exists.

---

## 3. Modifiers — the dial rewards patterns, not just volume

| rule | what triggers it | effect |
|---|---|---|
| **repetition** | the same sensor fires in 3 of the last 5 chunks | +0.5 |
| | ... more than 5 times | +1.0 |
| **escalation** | last 3 chunks total more than the previous 3 by over 1.0 | +1.0 |
| **combination** | 2 different sensors non-zero in the same chunk | +1.0 |
| | 3 or more different sensors | **+2.0**, and the chunk total is uncapped |
| **distress floor** | a level-2/3 word or a scream appears | the dial is *held* at that height for 20 chunks |
| **decay** | every chunk | −0.5, and −0.2 minimum when a chunk adds nothing |

Repetition and escalation are the difference between one shout in the car and
someone genuinely being hurt. Combination is the most important one: it means
words **add to** screams instead of competing with them.

---

## 4. The two gates — where weak evidence is thrown away

After all the adding, two filters run. They exist because a dial that moves for
everything is a dial people stop trusting.

1. **Voice-only cap.** If the only evidence is a *quiet* voice, the chunk is
   limited to **1.5** points. A shout alone stays a blip.
2. **Strong-evidence gate.** A chunk scores **0** unless at least one of these
   is true: voice is 2, an event is 2, a word is level 2 or 3, or the trained
   model fired. A lone glass-clink at 0.2, a stray "help" misheard as "apple",
   or background music with a beat none of it moves the dial.

3. **Silence guard.** If nothing was heard and the chunk is basically silent,
   the dial does not even decay — a quiet car is not evidence of safety.

---

## 5. Measured behaviour — real numbers, same code, 10 Oct 2026

These came from `test_dial_behaviours.py`, which sends real audio files through
the running brain. Full log: `dial_behaviour_log.txt`.

| scenario | dial ends at | label |
|---|---|---|
| highway traffic, 6 chunks | **0.0** | NORMAL |
| muffled traffic + road noise + engine, 6 chunks | **0.0** | NORMAL |
| one scream clip in quiet air | 9.0 | HIGH RISK |
| the same scream with traffic under it | 9.0 (identical) | HIGH RISK |
| four human cries in a row | **6.0** | ELEVATED |
| "help stop it" shouted over traffic | **7.0** | ELEVATED |
| screams + "bachao stop help police" | **22.2** | CRITICAL |
| quiet glass breaking then slaps | 0.0 | NORMAL (known gap) |
| one whispered "bachao", then silence | holds 3.0 for 42 s | CONCERNING |

Two things to read off this table:

* **Traffic no longer contaminates danger.** A scream scores exactly the same
  whether or not engines are running under it.
* **The gap that remains is quiet danger.** Soft impacts never clear the
  thresholds, so they score 0 and nothing else catches them. That is a
  *threshold* problem, and it is what training data is for.

---

## 6. What cannot move the dial

Worth stating, so nobody blames the wrong thing:

* **A word that was never transcribed.** The dictionary matches *text*. If no
  software turned the sound into words, the word sensor is silent, no matter how
  loudly someone said "bachao".
* **`sfx_training/` samples.** That folder trains a separate classifier used by
  the archive page. It has no influence on the dial at all.
* **Loudness on its own.** Loud but unrecognised audio is worth 1.5 and then
  gets gated to 0.
* **Silence.** Decay is capped at 0.5 per chunk, and a fully silent chunk does
  not decay.
* **A distress memory that has not been earned.** The 60-second hold needs a
  level-2/3 word or a genuine scream.

---

## 7. Where to change a number

| to change | edit |
|---|---|
| what a word is worth | `distress_keywords.json` (levels 3/2/1), restart the app |
| what loud counts as | `server.py` → `VOICE_SEV_MAP` |
| when a sound counts | `server.py` → `EVENT_SEVERITY` |
| points, decay, hold, the gates | `scoring_engine.py` → `DangerScorerConfig` |
| where yellow turns to red | `scoring_engine.py` → `DIAL_LEVELS` |
| chunk length | `config.py` → `CHUNK_DURATION` |

After any of these, re-measure with `python test_dial_behaviours.py` and read
the table back. Do not judge a threshold change by ear; the whole history of
this dial is a rule that sounded right and measured wrong.
