"""
Distress keyword matching - lives in the brain, not in a browser.

Why here: the word list is a decision input. If it is duplicated in each
client, the clients drift apart and one of them silently stops counting.
Any client that can transcribe sends plain text in the `transcript` field
of /upload_chunk; this module turns that text into word_severity 0-3.

Matching is word-boundary based, so "no" does not fire inside "cannot",
"note" or "nobody" - which the old substring scan did.
"""
import json
import os
import re
import unicodedata

KEYWORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "distress_keywords.json")

_cache = {"mtime": None, "patterns": []}


def _normalise(text):
    """lowercase, fold smart quotes, drop punctuation, collapse spaces"""
    t = unicodedata.normalize("NFKC", (text or "")).lower()
    t = t.replace("\u2019", "'").replace("\u2018", "'")
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _load():
    """Read the file once per change, so edits apply with a server restart
    (and would apply live if the mtime changed mid-run)."""
    try:
        mtime = os.path.getmtime(KEYWORDS_FILE)
    except OSError:
        if not _cache["patterns"]:
            print("[Keywords] WARNING: distress_keywords.json not found - "
                  "word severity will stay 0 for every client")
        return _cache["patterns"]

    if _cache["mtime"] == mtime:
        return _cache["patterns"]

    try:
        with open(KEYWORDS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (ValueError, OSError) as exc:
        print(f"[Keywords] WARNING: could not read distress_keywords.json ({exc})")
        return _cache["patterns"]

    patterns = []
    for level in ("3", "2", "1"):
        for phrase in data.get(level, []):
            norm = _normalise(phrase)
            if not norm:
                continue
            # flexible inner spacing: "bachao  mujhe" still matches
            body = r"\s+".join(re.escape(w) for w in norm.split(" "))
            patterns.append((norm, int(level),
                             re.compile(r"(?<![a-z0-9])" + body + r"(?![a-z0-9])")))
    _cache["mtime"] = mtime
    _cache["patterns"] = patterns
    print(f"[Keywords] Loaded {len(patterns)} distress phrases "
          f"from distress_keywords.json")
    return patterns


def match_words(text):
    """Return (severity 0-3, [phrases found]).  Highest severity wins."""
    patterns = _load()
    norm = _normalise(text)
    if not norm or not patterns:
        return 0, []

    found = []
    best = 0
    for phrase, level, rx in patterns:
        if rx.search(norm):
            # report the longest phrase only: "bachao mujhe", not also "bachao"
            if not any(f in phrase for f in found):
                found.append(phrase)
            best = max(best, level)
    return best, found


if __name__ == "__main__":
    tests = [
        "bachao", "bachao mujhe please", "stop the car", "I cannot do that",
        "gaari roko bhai", "madad karo", "there is no note in my phone",
        "he has a gun", "theek hai sir", "mar de", "BACHAO!", "no no please",
        "she said nothing about diets", "kameena", "ruko bhai",
    ]
    for t in tests:
        sev, kw = match_words(t)
        print(f"  sev={sev}  {t!r}  -> {kw}")
