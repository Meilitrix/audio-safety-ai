"""_patch_hook_type.py - repair a pre-existing TypeScript error in SaferRide.

`tsc --noEmit` reports two errors that existed BEFORE any change in this
session (git showed only SosPromptModal.tsx as modified, and these are in
App.tsx / useAudioSafety.ts):

  src/App.tsx(558,39): error TS2339: Property 'getAudioLevels' does not exist
      on type 'UseAudioSafetyReturn'.
  src/hooks/useAudioSafety.ts(217,109): error TS2353: ... 'getAudioLevels' does
      not exist in type 'UseAudioSafetyReturn'.

Cause: the hook defines and returns getAudioLevels (line 215 / 217) but its
declared return type (lines 28-36) never listed it. The dev server doesn't type
check, so `npm run dev` hides this - but `npm run build` fails on it.

Fix: declare the member. No behaviour changes.
"""
import io
import sys

PATH = r"C:\Users\user\Documents\Qoder\2026-09-14\chat-1\saferide-ai\src\hooks\useAudioSafety.ts"

OLD = """  startMonitoring: () => Promise<void>;
  stopMonitoring: () => void;
}"""
NEW = """  startMonitoring: () => Promise<void>;
  stopMonitoring: () => void;
  /** Rolling live loudness (0..1) for the waveform box; newest value last.
      Declared here because the hook returns it - without this line the
      production build fails type checking. */
  getAudioLevels: () => number[];
}"""

src = io.open(PATH, encoding="utf-8").read()
n = src.count(OLD)
if n != 1:
    print("REFUSING TO WRITE: the interface block matched %d times, expected 1" % n)
    sys.exit(1)

io.open(PATH, "w", encoding="utf-8", newline="\n").write(src.replace(OLD, NEW, 1))
print("patched useAudioSafety.ts")
print("  getAudioLevels now declared in the return type:", "getAudioLevels: () => number[];" in src.replace(OLD, NEW, 1))
