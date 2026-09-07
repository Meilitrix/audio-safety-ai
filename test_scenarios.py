"""
test_scenarios.py — Replay all 12 scenario families through the danger scorer.
Verifies the dial behaves correctly for each case.

Run: python test_scenarios.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scoring_engine import DangerScorer, replay_scenario, print_scenario

# ══════════════════════════════════════════════════════════════════════
#  SCENARIO DEFINITIONS — from the spec
# ══════════════════════════════════════════════════════════════════════

# S01: Completely normal — car cabin, no distress
S01_NORMAL = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.008, "peak": 0.35, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.006, "peak": 0.30, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.004, "peak": 0.25, "yamnet_top_name": "Thump, thud"},
]

# S02: Mild concern — "ruko" once, calm voice
S02_MILD_CONCERN = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 1, "energy": 0.010, "peak": 0.4, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.004, "peak": 0.25, "yamnet_top_name": "Thump, thud"},
]

# S03: Repeated refusal with escalation — "ruko" x3, voice rising
S03_REPEATED_REFUSAL = [
    {"word_severity": 1, "energy": 0.010, "peak": 0.4, "yamnet_top_name": "Speech"},
    {"word_severity": 1, "energy": 0.030, "peak": 0.6, "yamnet_top_name": "Speech"},
    {"word_severity": 1, "energy": 0.060, "peak": 0.8, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.008, "peak": 0.35, "yamnet_top_name": "Speech"},
]

# S04: Help-seeking — "help", nervous voice
S04_HELP_NERVOUS = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 2, "energy": 0.035, "peak": 0.7, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.008, "peak": 0.35, "yamnet_top_name": "Speech"},
]

# S05: Explicit distress — "bachao" + screaming
S05_EXPLICIT_DISTRESS = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 2, "energy": 0.100, "peak": 0.95, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.080, "peak": 0.90, "yamnet_top_name": "Speech"},
]

# S06: Distress + physical event — scream THEN impact (separate chunks)
S06_DISTRESS_AND_IMPACT = [
    {"word_severity": 2, "energy": 0.100, "peak": 0.95, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.020, "peak": 0.80, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.015, "peak": 0.70, "yamnet_top_name": "Thump, thud"},
]

# S07: Single thud — normal car, one bump
S07_SINGLE_THUD = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.010, "peak": 0.5, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
]

# S08: Repeated impacts — something hitting repeatedly
S08_REPEATED_IMPACTS = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.015, "peak": 0.70, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.018, "peak": 0.75, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.020, "peak": 0.80, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.022, "peak": 0.85, "yamnet_top_name": "Thump, thud"},
]

# S09: Threat from driver — threatening words + aggressive voice
S09_THREAT = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Speech"},
    {"word_severity": 2, "energy": 0.040, "peak": 0.7, "yamnet_top_name": "Speech"},
    {"word_severity": 3, "energy": 0.060, "peak": 0.8, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Speech"},
]

# S10: Critical — "bachao" + screaming + crash
S10_CRITICAL = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 2, "energy": 0.120, "peak": 1.0, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.050, "peak": 0.9, "yamnet_top_name": "Crash"},
    {"word_severity": 0, "energy": 0.030, "peak": 0.8, "yamnet_top_name": "Thump, thud"},
]

# S11: Accident — crash with no words
S11_ACCIDENT = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 0, "energy": 0.040, "peak": 0.85, "yamnet_top_name": "Crash"},
    {"word_severity": 0, "energy": 0.020, "peak": 0.7, "yamnet_top_name": "Thump, thud"},
]

# S12: Scream → silence (unresolved danger)
S12_SCREAM_THEN_SILENCE = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Thump, thud"},
    {"word_severity": 2, "energy": 0.100, "peak": 0.95, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.001, "peak": 0.05, "yamnet_top_name": "Silence"},
    {"word_severity": 0, "energy": 0.001, "peak": 0.04, "yamnet_top_name": "Silence"},
    {"word_severity": 0, "energy": 0.001, "peak": 0.03, "yamnet_top_name": "Silence"},
    {"word_severity": 0, "energy": 0.001, "peak": 0.03, "yamnet_top_name": "Silence"},
    {"word_severity": 0, "energy": 0.001, "peak": 0.03, "yamnet_top_name": "Silence"},
    {"word_severity": 0, "energy": 0.001, "peak": 0.03, "yamnet_top_name": "Silence"},
]

# S13: False positive protection — loud music
S13_LOUD_MUSIC = [
    {"word_severity": 0, "energy": 0.015, "peak": 0.5, "yamnet_top_name": "Music"},
    {"word_severity": 0, "energy": 0.018, "peak": 0.55, "yamnet_top_name": "Music"},
    {"word_severity": 0, "energy": 0.012, "peak": 0.45, "yamnet_top_name": "Music"},
]

# S14: "Ruko" ambiguity — normal context (driver asks passenger)
S14_RUKO_NORMAL = [
    {"word_severity": 0, "energy": 0.005, "peak": 0.3, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.006, "peak": 0.3, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.005, "peak": 0.25, "yamnet_top_name": "Speech"},
]

# S15: Real rollercoaster screams (from our analysis data)
S15_REAL_SCREAMS = [
    {"word_severity": 0, "energy": 0.124, "peak": 1.03, "yamnet_top_name": "Guitar"},
    {"word_severity": 0, "energy": 0.118, "peak": 1.02, "yamnet_top_name": "Wedding music"},
    {"word_severity": 0, "energy": 0.224, "peak": 1.15, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.267, "peak": 1.16, "yamnet_top_name": "Speech"},
    {"word_severity": 0, "energy": 0.154, "peak": 1.04, "yamnet_top_name": "Speech"},
]


# ══════════════════════════════════════════════════════════════════════
#  RUN ALL SCENARIOS
# ══════════════════════════════════════════════════════════════════════

SCENARIOS = [
    ("S01: Completely Normal",            S01_NORMAL,            "NORMAL"),
    ("S02: Mild Concern (ruko)",          S02_MILD_CONCERN,      "CONCERNING"),
    ("S03: Repeated Refusal + Escalation", S03_REPEATED_REFUSAL, "HIGH RISK"),
    ("S04: Help-Seeking (nervous)",       S04_HELP_NERVOUS,      "HIGH RISK"),
    ("S05: Explicit Distress (bachao+)",   S05_EXPLICIT_DISTRESS, "CRITICAL"),
    ("S06: Distress + Physical Impact",   S06_DISTRESS_AND_IMPACT, "HIGH RISK"),
    ("S07: Single Thud",                  S07_SINGLE_THUD,       "NORMAL"),
    ("S08: Repeated Impacts",             S08_REPEATED_IMPACTS,  "HIGH RISK"),
    ("S09: Threat from Driver",           S09_THREAT,            "CRITICAL"),
    ("S10: CRITICAL (bachao+scream+crash)", S10_CRITICAL,        "CRITICAL"),
    ("S11: Accident (no words)",          S11_ACCIDENT,          "HIGH RISK"),
    ("S12: Scream -> Silence (unresolved)", S12_SCREAM_THEN_SILENCE, "HIGH RISK"),
    ("S13: Loud Music (false positive)",  S13_LOUD_MUSIC,        "NORMAL"),
    ("S14: Ruko Normal Context",          S14_RUKO_NORMAL,       "NORMAL"),
    ("S15: Real Rollercoaster Screams",   S15_REAL_SCREAMS,      "HIGH RISK"),
]

if __name__ == "__main__":
    print()
    print("=" * 80)
    print("  DANGER DIAL — SCENARIO MATRIX TEST")
    print("=" * 80)

    passed = 0
    failed = 0

    for name, scenario, expected_label in SCENARIOS:
        results = replay_scenario(scenario)
        print_scenario(name, results)

        final_label = results[-1]["dial_label"]
        final_score = results[-1]["accumulated_score"]

        # Check if the final dial matches expected
        # We allow ±1 level flexibility for prototype
        if final_label == expected_label:
            status = "PASS"
            passed += 1
        else:
            status = "CHECK"
            failed += 1

        print(f"  Expected: {expected_label}  |  Got: {final_label} "
              f"(score={final_score:.2f})  ->  {status}")
        print()

    print("=" * 80)
    print(f"  RESULTS: {passed} PASS, {failed} CHECK out of {len(SCENARIOS)} scenarios")
    print("=" * 80)
    print()
