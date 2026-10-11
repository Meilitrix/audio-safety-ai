"""_patch_auto_sos.py - make the automated SOS actually open the emergency window.

Two files outside this workspace, so exact verified string replacements only:
if any block does not match once and only once, nothing is written.

WHY IT DID NOT FIRE (measured in the source, not guessed)

  SosPromptModal.tsx ran its 1-second countdown in an effect whose dependency
  list included `onConfirmSos`.  App.tsx defines handleConfirmSosFromPrompt as a
  plain function, so it is a NEW object on every render - and the ride re-renders
  every ~3 seconds as each audio chunk arrives.  React therefore tore down and
  rebuilt the interval on every chunk, so a "25 second" timer only advanced about
  one step per chunk (roughly 75 seconds), and could stall outright if chunks
  arrived faster than the tick.

  Worse, onConfirmSos() was called from INSIDE the setCountdown updater - a side
  effect during a state update, which <StrictMode> (main.tsx line 7) is allowed to
  run twice, and React is allowed to drop.

THE FIX
  - keep the callback in a ref, so the interval no longer depends on identity;
  - let the tick only decrement;
  - fire the dispatch exactly once from its own effect, guarded by a ref.

WHAT THE DISPATCH NOW DOES
  Same window the manual button opens - EmergencyDialerModal with Punjab Police 15,
  Rescue 1122 and the rider's saved contacts, starting its DIALING -> CONNECTED
  sequence - and the incident report says truthfully that it was automatic and that
  the rider did not answer, instead of claiming a human confirmed it.
"""
import io
import sys

MODAL = (r"C:\Users\user\Documents\Qoder\2026-09-14\chat-1\saferide-ai"
         r"\src\components\SosPromptModal.tsx")
APP = r"C:\Users\user\Documents\Qoder\2026-09-14\chat-1\saferide-ai\src\App.tsx"

OLD_TIMER = """  const [countdown, setCountdown] = useState(25);
  const [isPaused, setIsPaused] = useState(false);

  // Auto-countdown timer
  useEffect(() => {
    if (!isOpen) {
      setCountdown(25);
      setIsPaused(false);
      return;
    }

    if (isPaused) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          onConfirmSos();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen, isPaused, onConfirmSos]);
"""

NEW_TIMER = """  const [countdown, setCountdown] = useState(AUTO_SOS_SECONDS);
  const [isPaused, setIsPaused] = useState(false);

  // The callback is kept in a ref ON PURPOSE.  App.tsx hands down a brand new
  // function object on every render, and the ride re-renders every ~3 seconds as
  // each audio chunk arrives.  Listing it as a dependency used to tear down and
  // rebuild this 1-second interval on every chunk, so the countdown advanced one
  // step per chunk instead of one per second and never reliably reached zero -
  // the card appeared and nothing followed.  The interval now depends only on
  // what it genuinely uses.
  const confirmRef = useRef(onConfirmSos);
  useEffect(() => {
    confirmRef.current = onConfirmSos;
  }, [onConfirmSos]);
  const dispatchedRef = useRef(false);

  // The tick only counts down.  Dispatching happens in its own effect below,
  // because calling another component's state update from inside a state updater
  // is a side effect React may run twice (<StrictMode> is on) or drop.
  useEffect(() => {
    if (!isOpen) {
      setCountdown(AUTO_SOS_SECONDS);
      setIsPaused(false);
      dispatchedRef.current = false;
      return;
    }

    if (isPaused) return;

    const timer = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen, isPaused]);

  // Exactly once, when the countdown truly reaches zero: open the emergency
  // window, the same one the rider's manual SOS button opens.
  useEffect(() => {
    if (isOpen && !isPaused && countdown === 0 && !dispatchedRef.current) {
      dispatchedRef.current = true;
      confirmRef.current();
    }
  }, [isOpen, isPaused, countdown]);
"""

REPL_MODAL = [
    ('import React, { useState, useEffect } from "react";',
     'import React, { useState, useEffect, useRef } from "react";'),

    ('export const SosPromptModal: React.FC<SosPromptModalProps> = ({',
     '/** Seconds the rider gets to answer before the emergency window opens by\n'
     " *  itself.  Named so it can be changed once, honestly, instead of in two\n"
     " *  places (it used to be the literal 25 twice). */\n"
     "const AUTO_SOS_SECONDS = 25;\n\n"
     'export const SosPromptModal: React.FC<SosPromptModalProps> = ({'),

    (OLD_TIMER, NEW_TIMER),
]

REPL_APP = [
    ('      summary: `SOS confirmed. Alerted ${emergencyNumber} and ${emergencyContacts.length} contacts.`,',
     '      summary: `Automatic SOS: the safety countdown elapsed with no answer. '
     'Opening Police ${emergencyNumber}, Rescue 1122 and '\
     '${emergencyContacts.length} contacts.`,'),

    ('      detectedKeywords: ["sos_confirmed"],',
     '      detectedKeywords: ["auto_sos_countdown_elapsed"],'),

    ('      transcriptSnippet: "EMERGENCY SOS CONFIRMED",',
     '      transcriptSnippet: "AUDIO SAFETY DIAL REACHED CRITICAL - NO RIDER RESPONSE",'),

    ('        "SOS confirmed by rider",\n'
     '        `Alert sent to ${emergencyNumber}`,\n'
     '        `Notified ${emergencyContacts.length} contacts`,',
     '        "Audio Safety dial stayed at SOS level",\n'
     '        "Safety card shown; rider did not answer within the countdown",\n'
     '        `Emergency window opened for Police ${emergencyNumber} and Rescue 1122`,\n'
     '        `Notifying ${emergencyContacts.length} contacts`,'),
]


def apply(path, repls, label):
    src = io.open(path, encoding="utf-8").read()
    bad = []
    for i, (old, new) in enumerate(repls, 1):
        n = src.count(old)
        if n != 1:
            bad.append("  %s block %d matched %d times (need exactly 1)" % (label, i, n))
            continue
        src = src.replace(old, new, 1)
    if bad:
        print("REFUSING TO WRITE %s:" % path)
        print("\n".join(bad))
        return False
    io.open(path, "w", encoding="utf-8", newline="\n").write(src)
    print("patched %s" % path)
    for probe in ("onConfirmSos();", "[isOpen, isPaused, onConfirmSos]",
                  "SOS confirmed. Alerted", "sos_confirmed", "EMERGENCY SOS CONFIRMED"):
        print("   %-42s still there: %s" % (probe, probe in src))
    return True


ok = apply(MODAL, REPL_MODAL, "modal") and apply(APP, REPL_APP, "app")
sys.exit(0 if ok else 1)
