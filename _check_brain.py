"""_check_brain.py - is the brain actually processing chunks right now?

Prints one line per attempt so the answer is readable in a plain console.
Nothing here changes anything; it only asks questions.
"""
import io
import json
import struct
import time
import urllib.request
import wave

import ctypes
import ctypes.wintypes


def ram_mb():
    """Free RAM straight from Windows, no extra packages needed."""
    class STATUS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.wintypes.DWORD), ("dwMemoryLoad", ctypes.wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    s = STATUS()
    s.dwLength = ctypes.sizeof(STATUS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
    return s.ullTotalPhys / 1e6, s.ullAvailPhys / 1e6, s.dwMemoryLoad


total, avail, load = ram_mb()
print("RAM total %.0f MB | available %.0f MB | Windows says %d%% in use"
      % (total, avail, load))
print("(a TensorFlow + YAMNet + browser + node setup like this wants well over 1 GB free)")

python_pids = []
try:
    import subprocess
    out = subprocess.check_output(
        ["tasklist", "/FO", "CSV", "/NH"], text=True, errors="ignore")
    import csv as _csv
    for row in _csv.reader(out.splitlines(), delimiter=",", quotechar='"'):
        try:
            nm = row[0].strip('"').lower()
            mem = row[4].strip('"').replace(",", "").replace(" K", "").replace("K", "")
            if nm.startswith(("python", "node", "chrome", "msedge")) and int(mem) > 30000:
                python_pids.append((row[0], row[1], int(mem) / 1024.0))
        except Exception:
            continue
except Exception as e:
    print("(could not list processes: %s)" % e)
print("biggest memory users:")
for nm, pid, rss in sorted(python_pids, key=lambda x: -x[2])[:8]:
    print("   %-14s pid %-6s %6.0f MB" % (nm, pid, rss))

sr, n = 22050, 3 * 22050
buf = io.BytesIO()
w = wave.open(buf, "wb")
w.setnchannels(1)
w.setsampwidth(2)
w.setframerate(sr)
w.writeframes(struct.pack("<%dh" % n, *([6000] * n)))
w.close()
wav = buf.getvalue()

for idx in range(3):
    b = "zz"
    body = (("--" + b + "\r\nContent-Disposition: form-data; name=\"journey_id\"\r\n\r\nhealth_check\r\n"
             + "--" + b + "\r\nContent-Disposition: form-data; name=\"chunk_index\"\r\n\r\n%d\r\n" % idx
             + "--" + b + "\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"c.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode()
            + wav + ("\r\n--" + b + "--\r\n").encode())
    req = urllib.request.Request("http://127.0.0.1:5004/upload_chunk", data=body,
                                 headers={"Content-Type": "multipart/form-data; boundary=" + b})
    t = time.time()
    try:
        r = json.load(urllib.request.urlopen(req, timeout=200))
        print("chunk %d : ANSWWERED in %5.1f s | dial %.1f %s | peak %.4f | voice %s | model %s"
              % (idx, time.time() - t, r["dial_score"], r["dial_label"], r["peak"],
                 r["voice_severity"], ("%.0f%%" % (100 * r.get("chunk_model_prob", 0))) if r.get("chunk_model_prob") is not None else "-"))
    except Exception as e:
        print("chunk %d : FAILED after %5.1f s : %s %s" % (idx, time.time() - t, type(e).__name__, e))

total, avail, load = ram_mb()
print("RAM available after: %.0f MB (%d%% in use)" % (avail, load))
