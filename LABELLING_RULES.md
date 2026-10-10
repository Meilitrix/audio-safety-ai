# Labelling rules — how your clicks become training data

Read this before you label another journey. Your labels are the only thing the
trained model learns from, and there is one rule in the pipeline that quietly
changes what you mean. This page exists so that rule never surprises you again.

The code that does the converting is `train_model/train_from_recordings.py`,
lines 52–56.

---

## 1. What the pipeline actually does with your clicks

You make two kinds of marks in the archive:

* a **journey** label — "Mark all safe" or the danger button
* **chunk** marks inside a journey — danger / safe / ignore, per 3 seconds

The converter turns those into model samples using exactly this table:

| what you did | what the model is taught |
|---|---|
| journey marked **safe** | *every* chunk in it = SAFE. Chunk marks are ignored. |
| journey marked **danger**, chunk marked **danger** | DANGER |
| journey marked **danger**, chunk marked **safe** | SAFE |
| journey marked **danger**, chunk marked **ignore** / **skip** | **thrown away entirely** |
| journey marked **danger**, chunk **left unmarked** | ⚠️ **SAFE** — today this is **80 chunks** |
| journey with **no label at all** | skipped, contributes nothing |

That last warning row is the one that bites. In a danger journey, every chunk
you did not bother to mark is being presented to the model as *"nothing was
happening here"*. If you marked 4 chunks of danger in a 90-second journey, the
model received **26 chunks of "safe" from a real dangerous situation** — some of
which may have contained the lead-up or the aftermath of the same incident.

**Unmarked is not "unknown" to this pipeline. Unmarked means safe.**

---

## 2. The habit that fixes it

Inside a **danger** journey, don't leave anything unmarked. Use the three buttons
like this:

| you think... | mark it |
|---|---|
| something bad is audible right here | **danger** |
| I can hear this stretch clearly and it is calm | **safe** |
| I'm not sure / music is covering it / I'd have to listen again | **ignore** |

`ignore` costs you nothing — that chunk is simply not used. An unmarked chunk
costs you, because it becomes a confident wrong answer.

You do **not** need to mark every chunk of every journey by hand. The order that
pays most:

1. In each danger journey, mark the few seconds around each real incident as
   **danger** (you already do this).
2. Then scrub the *rest* and mark obvious calm stretches **safe** — engine,
   road noise, normal conversation.
3. Anything in between that you can't judge: select it and hit **ignore**.
   A rough rule: if a chunk could plausibly contain the incident, ignore it
   rather than call it safe.

---

## 3. Where your data stands today (10 Oct 2026)

From `saved_journeys/` and `train_model/models/model_chunks_metadata.json`:

| | |
|---|---|
| journeys recorded | 23 |
| journeys labelled | **23 — nothing unreviewed** |
| journey split | 17 danger, 6 safe |
| chunk marks | 71 danger, 11 safe, 24 ignore |
| samples the model was trained on | **277** = 206 safe + 71 danger |
| model | SVM (RBF), cross-validated F1 **0.786** |

Read the last two rows together. Counting every chunk of every labelled journey
the way the converter does, the 206 "safe" samples break down like this:

| where a "safe" sample came from | chunks |
|---|---|
| you said so (a safe journey, or a chunk you marked safe) | **126** |
| **you left it unmarked inside a danger journey** | **80** |

So **39% of the model's "safe" teaching is a guess the pipeline made on your
behalf**, from danger journeys where only the incidents themselves were marked.
That is the most likely reason F1 moved *down* (0.802 → 0.786) while you were
adding more data: the extra samples were not better truth, they were more
guessed-safe. (These three numbers add up to the 277 in the metadata file, which
is how I checked the count against the trainer rather than by eye.)

You already label noise as safe, and that is exactly right — it is what teaches
the model that **loud is not the same as dangerous**. Keep doing it. The missing
half is *deciding on purpose* instead of leaving it blank.

---

## 4. What to record next, in priority order

The model is one sensor on the dial: the only one that can catch a danger that
is **quiet**. So record for that job, not for volume.

| priority | record | why it pays |
|---|---|---|
| **1** | finish the marks on journeys you already have | free, and it removes actively wrong labels |
| **2** | **loud but harmless** — music with bass, horn, engine revs, indicator clicking, AC, someone arguing on speaker phone, a phone ringing in the car | the model's job is to say *no* to these; every one you label safe protects the rider from a false alarm |
| **3** | **quiet danger** — crying at low volume, a scuffle under music, whispered distress, a soft hit against a car panel | the rules cannot see this at all (measured: quiet glass + slaps scored **0.0**). Only labelled data can teach it |
| **4** | **your own voice saying the distress words** at road-noise level | this is really a *transcription* test — it tells us whether words survive the trip to the dial |
| **5** | danger journeys from a **different car, room and microphone** | otherwise the model may learn the sound of one microphone instead of danger |
| **6** | parked-and-silent, and empty-room hum | the "silence is not safety" case, and it keeps the model honest at night |

Rough target: **30–50 deliberate danger chunks and a similar number of
deliberate safe chunks per situation type**. Two safe + two danger is the bare
minimum to train at all; it is not enough to be worth trusting.

---

## 5. After training, check before you trust

1. Press **Train from labelled journeys** (or the Risk Analysis Trainer button).
2. Open `train_model/models/model_chunks_metadata.json` — look at
   `n_safe` / `n_danger` and `cv_f1_macro`.
3. Run `python eval_chunk_model.py` for precision and recall on your own data.
4. Run `python test_dial_behaviours.py` — the scenario table tells you whether
   the dial still refuses to move for traffic. **This is the check that matters:
   a model can score well on paper and still alarm on an engine.**

If F1 goes up but benign traffic starts climbing the dial, the model is not
better — it is just differently wrong. Add more category-2 data, not more danger.

---

## 6. Two things labelling will never do

* **It will not change what a distress word is worth.** Words are hand-written
  rules in `distress_keywords.json`, not training. Adding labels cannot make
  "bachao" score higher.
* **It will not change the dial's decay, thresholds or colours.** Those are
  arithmetic in `scoring_engine.py`.

Labelling only improves the one sensor that needs examples. When the dial
behaves wrongly, check `DIAL_ARITHMETIC.md` first — most dial complaints are a
rule, not a model.
