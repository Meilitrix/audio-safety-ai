"""_patch_sos_popup.py - soften the SaferRide SOS popup (colours + wording).

SaferRide lives outside this workspace, so the editor cannot reach it directly.
This script does exact, verified string replacements: if any block is not found
once and only once, it refuses to write anything.

What changes and why:
  - red border / red badge / red octagon  -> calm cyan, life-buoy icon. The
    popup is a safety CHECK, not an alarm; the rider may be perfectly fine.
  - "3 risk patterns were detected"       -> plain language. The number was a
    hardcoded 3 in App.tsx, so it was never a real measurement. Removed.
  - "Auto-dialing Police in 25s"          -> "The emergency screen opens in".
    Nothing dials by itself, so the old text claimed something the code does
    not do - and it is the scariest possible sentence for a calm rider.
  - solid red "Call Police (Emergency SOS)" button -> quiet outline.
  - "Cancel - I am Safe / False Alarm"    -> "I am safe", made the primary
    green button, because most of the time that IS the answer.
  - footer note corrected: pressing it does NOT reset the audio dial; it only
    closes this card (the brain keeps its own score).
Nothing about the behaviour, the timer, or the button ids is touched.
"""
import io
import os
import sys

PATH = os.path.join(
    r"C:\Users\user\Documents\Qoder\2026-09-14\chat-1\saferide-ai\src\components",
    "SosPromptModal.tsx",
)

REPL = [
    # 1. icon swap
    ('import { AlertOctagon, PhoneCall, ShieldCheck, Clock, Pause, Play } from "lucide-react";',
     'import { LifeBuoy, PhoneCall, ShieldCheck, Clock, Pause, Play } from "lucide-react";'),

    # 2. stop reading riskCount (the value passed in is a hardcoded 3)
    ("  riskCount,\n  emergencyNumber,\n}) => {",
     "  // riskCount is intentionally not shown: App.tsx passes a fixed 3, so any\n"
     "  // number printed here would be invented rather than measured.\n"
     "  emergencyNumber,\n}) => {"),

    # 3. card border: red -> neutral
    ('<div className="bg-slate-900 border border-red-500/70 max-w-md w-full rounded-3xl p-6 shadow-2xl text-white space-y-5 relative">',
     '<div className="bg-slate-900 border border-slate-700 max-w-md w-full rounded-3xl p-6 shadow-2xl text-white space-y-5 relative">'),

    # 4. icon tile: red -> calm cyan
    ('<div className="w-12 h-12 rounded-2xl bg-red-600/20 border border-red-500/40 text-red-400 flex items-center justify-center shrink-0">\n            <AlertOctagon className="w-6 h-6" />',
     '<div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-400/30 text-cyan-300 flex items-center justify-center shrink-0">\n            <LifeBuoy className="w-6 h-6" />'),

    # 5. badge
    ('<span className="text-[11px] font-semibold text-red-400 bg-red-950/80 px-2 py-0.5 rounded border border-red-800/80">\n              Safety Check Triggered',
     '<span className="text-[11px] font-semibold text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/50">\n              Safety check'),

    # 6. subtitle
    ("              {riskCount} risk patterns were detected in the last 60 seconds.",
     "              The ride monitor has been alarmed for the last minute."),

    # 7. countdown wording
    ("                  Auto-dialing Police in{\" \"}",
     "                  The emergency screen opens in{\" \"}"),

    # 8. cancel button becomes the calm, primary green action
    ('className="w-full py-3.5 px-4 bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700 hover:border-emerald-500/50 font-bold text-sm rounded-xl flex items-center justify-center gap-2 shadow transition-all"\n          >\n            <ShieldCheck className="w-5 h-5 text-emerald-400" />\n            <span>Cancel — I am Safe / False Alarm</span>',
     'className="w-full py-3.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-500 font-bold text-sm rounded-xl flex items-center justify-center gap-2 shadow transition-all"\n          >\n            <ShieldCheck className="w-5 h-5 text-white" />\n            <span>I am safe</span>'),

    # 9. emergency button becomes an outline, not a solid red block
    ('className="w-full py-3.5 px-4 bg-red-600 hover:bg-red-500 text-white font-bold text-sm rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-red-600/30 transition-all"\n          >\n            <PhoneCall className="w-4 h-4 text-white" />\n            <span>Call Police {emergencyNumber} (Emergency SOS)</span>',
     'className="w-full py-3 px-4 bg-transparent hover:bg-rose-950/50 text-rose-300 border border-rose-500/50 font-semibold text-sm rounded-xl flex items-center justify-center gap-2 transition-all"\n          >\n            <PhoneCall className="w-4 h-4 text-rose-300" />\n            <span>Call Police {emergencyNumber}</span>'),

    # 10. footer: say what actually happens
    ('          Clicking "Cancel" resets the safety monitor back to normal.',
     '          "I am safe" closes this. The audio monitor keeps listening.'),
]

if not os.path.exists(PATH):
    print("NOT FOUND:", PATH)
    sys.exit(1)

src = io.open(PATH, encoding="utf-8").read()
before = src

problems = []
for i, (old, new) in enumerate(REPL, 1):
    n = src.count(old)
    if n != 1:
        problems.append("  block %d found %d times (expected exactly 1)" % (i, n))
        continue
    src = src.replace(old, new, 1)

if problems:
    print("REFUSING TO WRITE - these replacements did not match cleanly:")
    print("\n".join(problems))
    sys.exit(1)

io.open(PATH, "w", encoding="utf-8", newline="\n").write(src)
print("patched", os.path.basename(PATH))
print("  length %d -> %d bytes" % (len(before), len(src)))
for token in ("border-red-500/70", "AlertOctagon", "Auto-dialing Police",
              "risk patterns were detected", "bg-red-600", "False Alarm",
              "resets the safety monitor"):
    print("  %-34s still present: %s" % (token, token in src))
