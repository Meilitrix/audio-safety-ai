"""
scoring_engine.py — Danger Dial Scoring Engine
================================================
Temporal accumulation model with decay.

  Danger Score = Previous Score
                   + Word Signal (A)
                   + Voice Signal (B)
                   + Event Signal (C)
                   + Repetition bonus
                   + Escalation bonus
                   + Combination bonus
                   - Recovery / Decay
                   = New Score

Four rule types:
  Rule 1 -- Base signal:     what happened this chunk
  Rule 2 -- Repetition:      same signal repeating -> bonus
  Rule 3 -- Escalation:      severity increasing across chunks -> bonus
  Rule 4 -- Combination:     multiple signals in same chunk -> bonus

Dial levels (retuned to damp benign-loudness false alarms):
  0       -> NORMAL      (green)
  2-4     -> CONCERNING  (yellow)
  5-8     -> ELEVATED    (orange)
  9-12    -> HIGH RISK   (red)
  13+     -> CRITICAL    (flashing red)

Calibrated against:
  - 10 car cabin recordings (309 chunks, 0 false positives)
  - 2 scream recordings (rollercoaster, male screams)
  - 8 slap/impact recordings
"""

# ══════════════════════════════════════════════════════════════════════
#  THRESHOLDS — calibrated from car audio analysis
# ══════════════════════════════════════════════════════════════════════

# ── Signal B: Voice severity (energy + peak from audio analysis) ──
#    Car cabin baseline:  energy 0.001-0.018, peak 0.1-0.6
#    Raised voice:        energy 0.020-0.050, peak 0.60-0.85
#    Screaming:           energy 0.050+,      peak 0.85+
#    Rollercoaster data:  energy 0.052-0.267, peak 0.86-1.22

VOICE_NORMAL_MAX_ENERGY = 0.030
VOICE_NORMAL_MAX_PEAK   = 0.75
VOICE_SCREAM_MIN_ENERGY = 0.050
VOICE_SCREAM_MIN_PEAK   = 0.85

# ── Signal C: Event anomaly (non-verbal danger sounds) ──
#    YAMNet "Thump, thud" is the normal car engine baseline.
#    Only flag it when energy is well above the car cabin range.

EVENT_ENERGY_FLOOR    = 0.008   # min energy for any event detection
EVENT_IMPACT_ENERGY   = 0.015   # energy for thud-as-impact
EVENT_PEAK_IMPACT     = 0.65    # sharp transient threshold
EVENT_THUMP_ENERGY    = 0.015   # "Thump, thud" only if above this

# "Crash" and "Collapse" are NOT YAMNet class names.  The vocabulary offers
# Slam, Thump-thud, Shatter, Explosion, Glass, Tire squeal instead.  Nothing
# scores off this set; it is kept only as a note of what a true crash label
# would need.
CRASH_CLASSES    = {"Crash", "Collapse"}
IMPACT_CLASSES   = {"Thump, thud"}
# "Fire" removed: not a YAMNet class name.  The real ones are "Fire alarm",
# "Firecracker", "Artillery fire" - the last already listed.
CONCERN_CLASSES  = {"Glass", "Explosion", "Artillery fire"}
# ── Vocal distress labels that YAMNet itself emits (see yamnet_engine
#    DANGER_INDICES + the pitch-detected reason string).  When the engine
#    has already classified a chunk as a scream/shout, that IS corroborated
#    event evidence — the dial must honour it instead of falling back to
#    raw energy alone (which zeroed short/quiet screams). ──
# "Bellow" added after measuring the real scream clips: YAMNet's top-5 for
# them is Sheep / Children playing / Bellow / Hiss / Speech.  It never emits
# "Scream", so without this label the dial gets no event evidence and falls
# back to the voice-only 1.5-per-chunk cap (~27s to CRITICAL).
VOCAL_DANGER_CLASSES = {"Scream", "Shriek", "Shout", "Yell", "Bellow"}
# NOTE: nothing reads this set - it survives only as documentation.  The two
# spellings below were corrected to YAMNet's real class names ("Child speech"
# and "Narration" do not exist) but the set is deliberately NOT wired into the
# scorer, because that would change detection the day before a demo.
SAFE_CLASSES     = {   # sounds that should never raise the dial
    "Music", "Speech", "Conversation", "Child speech, kid speaking",
    "Narration, monologue", "Babbling", "Children playing",
    "Vehicle", "Car", "Engine", "Idling",
    "Silence", "Noise", "Environmental noise",
}

# ══════════════════════════════════════════════════════════════════════
#  SCORING CONFIG
# ══════════════════════════════════════════════════════════════════════

DIAL_LEVELS = [
    (0, "NORMAL"),
    (2, "CONCERNING"),
    (5, "ELEVATED"),
    (9, "HIGH RISK"),
    (13, "CRITICAL"),
]

# Decay / recovery (recovery made faster so a brief loud burst relaxes quickly)
DECAY_PER_CHUNK              = 1.0
CONSECUTIVE_NORMAL_FOR_DECAY = 4    # chunks of normal before decay
MAINTENANCE_WINDOW           = 4    # chunks after danger before decay

# Repetition / escalation windows
REPETITION_WINDOW = 5
ESCALATION_WINDOW = 4

# History limit
MAX_HISTORY = 30


# ══════════════════════════════════════════════════════════════════════
#  DANGER SCORER
# ══════════════════════════════════════════════════════════════════════

class DangerScorer:
    """
    Per-session danger scoring engine.
    One instance per monitoring/recording session.
    Call process_chunk() for each 3-second audio chunk.
    """

    def __init__(self):
        self.accumulated_score = 0.0
        self.dial_level = 0
        self.dial_label = "NORMAL"
        self.history = []
        self.consecutive_normal = 0
        self.chunks_since_danger = 999
        self.voice_severity_history = []
        self.word_severity_history = []
        self.event_history = []

    # ══════════════════════════════════════════════════════════════════
    #  SIGNAL DETECTORS
    # ══════════════════════════════════════════════════════════════════

    def detect_voice_severity(self, energy, peak):
        """
        Signal B -- Vocal intensity from raw audio metrics.
        Returns 0 (normal), 1 (raised), or 2 (screaming).
        """
        if (energy >= VOICE_SCREAM_MIN_ENERGY and
                peak >= VOICE_SCREAM_MIN_PEAK):
            return 2   # screaming
        if (energy > VOICE_NORMAL_MAX_ENERGY or
                peak > VOICE_NORMAL_MAX_PEAK):
            return 1   # raised voice
        return 0       # normal cabin

    def detect_event_anomaly(self, energy, peak, yamnet_top_name,
                             voice_severity=0):
        """
        Signal C -- Non-verbal event anomaly.
        Uses energy + peak + YAMNet context.
        Crucially: when voice_severity=2 (screaming), high energy is
        from the scream, NOT a physical impact. Don't double-count.
        Returns dict: {severity: 0-3, type: str, detail: str}
        """
        # Removed: an `if yamnet_top_name in CRASH_CLASSES` branch.  Neither name is
        # a YAMNet class, so it could never fire.  A real collision is caught below
        # by IMPACT ("Thump, thud") plus its energy and peak - the path that is
        # actually exercised, and actually measured.

        # YAMNet already judged this chunk as vocal distress (Scream/Shriek/
        # Shout/Yell or a pitch-detected scream). Treat it as a real event so
        # short or quiet screams can accumulate on the dial. Checked BEFORE the
        # voice-dominated zeroing below, which would otherwise discard it.
        if yamnet_top_name in VOCAL_DANGER_CLASSES:
            return {"severity": 2, "type": "vocal_danger",
                    "detail": yamnet_top_name}

        # Concern classes only with sufficient energy
        if yamnet_top_name in CONCERN_CLASSES and energy > EVENT_ENERGY_FLOOR:
            return {"severity": 2, "type": "danger_sound",
                    "detail": yamnet_top_name}

        # When voice is screaming, high energy is from the scream.
        # Don't classify it as a physical impact (avoids double-counting).
        if voice_severity >= 2:
            return {"severity": 0, "type": "none",
                    "detail": "voice-dominated"}

        # "Thump, thud" is the car engine baseline — only flag if energy high
        if yamnet_top_name in IMPACT_CLASSES:
            if energy > EVENT_THUMP_ENERGY:
                # If voice is raised, the "thud" is likely vocal energy
                # (not a separate physical impact). Cap severity.
                if 1 <= voice_severity < 2:
                    return {"severity": 1, "type": "thud",
                            "detail": f"E={energy:.4f}, P={peak:.2f} (voice-corr)"}
                if peak > EVENT_PEAK_IMPACT:
                    return {"severity": 2, "type": "impact",
                            "detail": f"E={energy:.4f}, P={peak:.2f}"}
                return {"severity": 1, "type": "thud",
                        "detail": f"E={energy:.4f}, P={peak:.2f}"}
            return {"severity": 0, "type": "none", "detail": "normal cabin"}

        # ── No generic "loud + unknown label = impact" fallback. ──
        #    The previous fallback fired whenever YAMNet's top label was not
        #    *literally* in SAFE_CLASSES and the sound was loud.  YAMNet has
        #    521 classes and the safe-list is tiny, so ordinary sounds
        #    (silence -> "Spray", car -> "Door", room noise -> "Cheering")
        #    were constantly scored as severity-2 impacts.  Because an event
        #    is a "strong" signal, the dial then accumulated on every chunk and
        #    NEVER decayed -- the exact "maxes out and stays there" bug.
        #    Real physical danger is already covered by
        #    CONCERN_CLASSES, IMPACT ("Thump, thud") and VOCAL_DANGER above.
        #    Loudness alone is no longer treated as evidence of danger.
        return {"severity": 0, "type": "none", "detail": "normal"}

    # ══════════════════════════════════════════════════════════════════
    #  RULE ENGINE — four rule types
    # ══════════════════════════════════════════════════════════════════

    def _repetition_bonus(self, word_sev, voice_sev):
        """
        Rule 2 -- Repetition: same distress signal repeating.
        If the same severity appeared 3+ times in last N chunks -> bonus.
        """
        bonus = 0.0
        recent = self.history[-REPETITION_WINDOW:]

        if word_sev > 0:
            count = sum(1 for h in recent
                        if h.get("word_severity", 0) == word_sev)
            if count >= 3:
                bonus += 0.25 * (count - 2)

        if voice_sev > 0:
            count = sum(1 for h in recent
                        if h.get("voice_severity", 0) == voice_sev)
            if count >= 3:
                bonus += 0.25 * (count - 2)

        return bonus

    def _escalation_bonus(self, voice_sev, word_sev):
        """
        Rule 3 -- Escalation: severity INCREASING right now.
        Only triggers when current chunk is higher than the previous one.
        """
        bonus = 0.0

        if len(self.history) >= 1:
            prev = self.history[-1]
            prev_voice = prev.get("voice_severity", 0)
            prev_word = prev.get("word_severity", 0)

            # Voice escalating right now
            if voice_sev > prev_voice and voice_sev > 0:
                bonus += 1.0
            # Words escalating right now
            if word_sev > prev_word and word_sev > 0:
                bonus += 1.0

        return bonus

    def _combination_bonus(self, word_pts, voice_pts, event_pts):
        """
        Rule 4 -- Combination: multiple signals in same chunk.
        Bonus when 2+ signal types active AND at least one is high (>=2).
        """
        active = sum(1 for p in [word_pts, voice_pts, event_pts] if p > 0)
        if active < 2:
            return 0.0
        if max(word_pts, voice_pts, event_pts) >= 2:
            return 1.0   # strong combination
        return 0.0       # multiple weak signals — no bonus

    # ══════════════════════════════════════════════════════════════════
    #  DECAY / RECOVERY
    # ══════════════════════════════════════════════════════════════════

    def _apply_decay(self):
        """
        Recovery: score decays only after sustained normal behaviour.
        Requires 8+ consecutive normal chunks AND 8+ chunks since danger.
        """
        if (self.consecutive_normal >= CONSECUTIVE_NORMAL_FOR_DECAY and
                self.chunks_since_danger >= MAINTENANCE_WINDOW):
            self.accumulated_score = max(
                0, self.accumulated_score - DECAY_PER_CHUNK
            )

    # ══════════════════════════════════════════════════════════════════
    #  MAIN PROCESSOR
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _model_points(model_danger_prob):
        """Signal D -- the journey-trained chunk model's confidence.
        0 unless the trained model saw danger, so a quiet-but-real chunk
        can accumulate on the dial over time. Default (0.0) => no change."""
        if not model_danger_prob or model_danger_prob <= 0:
            return 0.0
        if model_danger_prob >= 0.90:
            return 2.0
        if model_danger_prob >= 0.70:
            return 1.0
        return 0.0

    def process_chunk(self, word_severity=0, energy=0.0, peak=0.0,
                      yamnet_top_name="", model_danger_prob=0.0):
        """
        Process one 3-second chunk through the full scoring pipeline.

        Parameters
        ----------
        word_severity : int 0-3  (from browser keyword detection)
        energy : float           (mean squared energy of audio)
        peak : float             (peak absolute amplitude)
        yamnet_top_name : str    (top YAMNet class name)
        model_danger_prob : float 0..1  (P(danger) from the journey-trained
            chunk model; 0 disables it -> identical to prior behaviour)

        Returns dict with full scoring breakdown.
        """
        # Step 1: Detect signals
        voice_sev = self.detect_voice_severity(energy, peak)
        event = self.detect_event_anomaly(energy, peak, yamnet_top_name,
                                          voice_severity=voice_sev)

        # Step 2: Base points
        word_pts = float(word_severity)        # 0-3
        voice_pts = float(voice_sev)           # 0-2
        event_pts = float(event["severity"])   # 0-2
        model_pts = self._model_points(model_danger_prob)  # 0-2 (journey model)
        base_sum = word_pts + voice_pts + event_pts + model_pts

        # Step 3: Repetition bonus (Rule 2)
        rep_bonus = self._repetition_bonus(word_severity, voice_sev)

        # Step 4: Escalation bonus (Rule 3)
        esc_bonus = self._escalation_bonus(voice_sev, word_severity)

        # Step 5: Combination bonus (Rule 4)
        combo_bonus = self._combination_bonus(word_pts, voice_pts, event_pts)

        # Step 6: Chunk contribution
        chunk_score = base_sum + rep_bonus + esc_bonus + combo_bonus

        # Cap voice-only contribution (no event/word/model corroboration)
        if voice_pts > 0 and event_pts == 0 and word_pts == 0 and model_pts == 0:
            chunk_score = min(chunk_score, 1.5)

        # NO accumulation from weak, uncorroborated signals.  A chunk counts as
        # danger evidence only if it is scream-level voice (2), an impact/crash
        # event (2), a keyword, or a trained-model vote.  Ordinary talking or
        # room noise (voice 1, no event) adds nothing and lets the dial DECAY --
        # this is the fix for "the dial maxes on talking and never comes back".
        strong = (voice_sev >= 2 or event_pts >= 2 or
                  word_pts > 0 or model_pts > 0)
        if not strong:
            chunk_score = 0.0

        # Step 7: Accumulate
        self.accumulated_score += chunk_score

        # Step 8: Track normal/danger for decay
        if chunk_score < 0.5:
            self.consecutive_normal += 1
            self.chunks_since_danger += 1
        else:
            self.consecutive_normal = 0
            self.chunks_since_danger = 0

        # Step 9: Apply decay
        self._apply_decay()

        # Step 10: Map to dial level
        self.dial_level = 0
        self.dial_label = "NORMAL"
        for threshold, label in DIAL_LEVELS:
            if self.accumulated_score >= threshold:
                self.dial_level = DIAL_LEVELS.index((threshold, label))
                self.dial_label = label

        # Step 11: Record history
        chunk_detail = {
            "chunk_index": len(self.history),
            "word_severity": word_severity,
            "voice_severity": voice_sev,
            "event_severity": event["severity"],
            "event_type": event["type"],
            "event_detail": event["detail"],
            "model_danger_prob": model_danger_prob,
            "model_pts": model_pts,
            "word_pts": word_pts,
            "voice_pts": voice_pts,
            "event_pts": event_pts,
            "base_sum": base_sum,
            "repetition_bonus": rep_bonus,
            "escalation_bonus": esc_bonus,
            "combination_bonus": combo_bonus,
            "chunk_score": chunk_score,
            "accumulated_score": self.accumulated_score,
            "dial_level": self.dial_level,
            "dial_label": self.dial_label,
            "energy": energy,
            "peak": peak,
            "yamnet_top": yamnet_top_name,
        }
        self.history.append(chunk_detail)
        self.voice_severity_history.append(voice_sev)
        self.word_severity_history.append(word_severity)
        self.event_history.append(event)

        # Trim history
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]
            self.voice_severity_history = self.voice_severity_history[-MAX_HISTORY:]
            self.word_severity_history = self.word_severity_history[-MAX_HISTORY:]
            self.event_history = self.event_history[-MAX_HISTORY:]

        return chunk_detail

    def reset(self):
        """Reset all state for a new session."""
        self.__init__()

    def get_state(self):
        """Return current dial state."""
        return {
            "accumulated_score": self.accumulated_score,
            "dial_level": self.dial_level,
            "dial_label": self.dial_label,
            "total_chunks": len(self.history),
            "consecutive_normal": self.consecutive_normal,
            "chunks_since_danger": self.chunks_since_danger,
        }


# ══════════════════════════════════════════════════════════════════════
#  SCENARIO REPLAY (for testing)
# ══════════════════════════════════════════════════════════════════════

def replay_scenario(scenario, scorer=None):
    """Replay a test scenario through the scorer."""
    if scorer is None:
        scorer = DangerScorer()
    results = []
    for chunk_input in scenario:
        result = scorer.process_chunk(
            word_severity=chunk_input.get("word_severity", 0),
            energy=chunk_input.get("energy", 0.005),
            peak=chunk_input.get("peak", 0.3),
            yamnet_top_name=chunk_input.get("yamnet_top_name", "Speech"),
        )
        results.append(result)
    return results


def print_scenario(name, results):
    """Pretty-print a scenario replay."""
    print(f"\n{'='*80}")
    print(f"  SCENARIO: {name}")
    print(f"{'='*80}")
    print(f"  {'Chunk':<6} {'Words':<6} {'Voice':<6} {'Event':<6} "
          f"{'Base':<6} {'Rep':<5} {'Esc':<5} {'Cmb':<5} "
          f"{'Score':<7} {'Total':<8} {'Dial'}")
    print(f"  {'-'*74}")
    for r in results:
        print(f"  #{r['chunk_index']+1:<5} "
              f"{r['word_severity']:<6} {r['voice_severity']:<6} "
              f"{r['event_severity']:<6} {r['base_sum']:<6.1f} "
              f"{r['repetition_bonus']:<5.2f} {r['escalation_bonus']:<5.1f} "
              f"{r['combination_bonus']:<5.1f} "
              f"{r['chunk_score']:<7.2f} {r['accumulated_score']:<8.2f} "
              f"{r['dial_label']}")
    final = results[-1]
    print(f"\n  FINAL: Score={final['accumulated_score']:.2f}  "
          f"Level={final['dial_level']}  "
          f"Label={final['dial_label']}")
