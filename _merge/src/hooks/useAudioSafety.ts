import { useState, useRef, useCallback, useEffect } from "react";

// The audio brain runs on the same machine, port 5004.  Derive the host from
// the page so a phone on the same Wi-Fi (http://192.168.x.x:5008) still reaches
// it - hardcoding "localhost" only ever worked on the laptop itself.
const AUDIO_HOST = import.meta.env.VITE_AUDIO_HOST || window.location.hostname || "localhost";
const AUDIO_SERVER = `http://${AUDIO_HOST}:5004`;

// The engine's dial runs 0..13, where 13 == CRITICAL (see scoring_engine
// DIAL_LEVELS: NORMAL 0, CONCERNING 2, ELEVATED 5, HIGH RISK 9, CRITICAL 13).
// The gauge is drawn as a percentage of THAT scale, not an invented one.
const DIAL_FULL_SCALE = 13;

export type MonitorStatus = "idle" | "connecting" | "live" | "disconnected";

interface AudioSafetyResult {
  status: string;
  confidence: number;
  sound_name: string;
  dial_score: number;
  dial_label: string;
  dial_level: number;
  word_severity: number;
  voice_severity: number;
  event_severity: number;
  event_type: string;
  transcript: string;
  keywords: string[];
  risk_level: number;
  custom_label?: string;
  custom_confidence?: number;
}

interface UseAudioSafetyReturn {
  isMonitoring: boolean;
  /** Explicit lifecycle so the UI can show "Safety AI disconnected" instead of
      silently freezing the last gauge value when the brain is unreachable. */
  monitorStatus: MonitorStatus;
  distressScore: number;
  dialLabel: string;
  lastResult: AudioSafetyResult | null;
  transcript: string;
  startMonitoring: () => Promise<void>;
  stopMonitoring: () => void;
  /** Rolling live loudness (0..1) for the waveform box; newest value last. */
  getAudioLevels: () => number[];
}

export function useAudioSafety(
  onThreatUpdate: (threatLevel: string, distressScore: number) => void
): UseAudioSafetyReturn {
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [monitorStatus, setMonitorStatus] = useState<MonitorStatus>("idle");
  const [distressScore, setDistressScore] = useState(0);
  const [dialLabel, setDialLabel] = useState("NORMAL");
  const [lastResult, setLastResult] = useState<AudioSafetyResult | null>(null);
  const [transcript, setTranscript] = useState("");

  const streamRef = useRef<MediaStream | null>(null);
  // Rolling live loudness (0..1) for the waveform box.  Newest at the end.
  const levelsRef = useRef<number[]>(new Array(28).fill(0));
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const chunkBufRef = useRef<Float32Array[]>([]);
  const chunkIdxRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const journeyIdRef = useRef("");
  const monitoringRef = useRef(false);
  // Three consecutive upload failures = the brain is gone. One success resets it.
  const failStreakRef = useRef(0);
  // Browser-side live transcription (Web Speech API). The Python brain has no
  // speech-to-text, so this hook is the ONLY thing that can put spoken words
  // in front of the dial. heardSinceChunkRef holds the words captured since
  // the last chunk was uploaded; recogRef is the running recogniser.
  const heardSinceChunkRef = useRef("");
  const recogRef = useRef<any>(null);

  const sendChunk = useCallback(async (wavBlob: Blob, idx: number) => {
    if (!monitoringRef.current) return;
    const form = new FormData();
    form.append("audio", wavBlob, `chunk_${idx}.wav`);
    form.append("journey_id", journeyIdRef.current);
    form.append("chunk_index", String(idx));
    // Forward the words heard since the last chunk. server.py runs distress-
    // keyword matching (match_words) on this to set word_severity, so spoken
    // "help"/"bachao" can now actually raise the dial. Without this the mic
    // was acoustics-only and distress words were ignored.
    const words = heardSinceChunkRef.current.trim();
    heardSinceChunkRef.current = "";
    form.append("transcript", words);

    try {
      const res = await fetch(`${AUDIO_SERVER}/upload_chunk`, { method: "POST", body: form });
      const data: AudioSafetyResult = await res.json();
      if (!monitoringRef.current) return;

      failStreakRef.current = 0;
      setMonitorStatus("live");
      setLastResult(data);
      setDialLabel(data.dial_label || "NORMAL");

      const score = Math.min(100, (data.dial_score / DIAL_FULL_SCALE) * 100);
      setDistressScore(score);

      // Transcript state is driven by the browser recogniser below (the source
      // of truth), not echoed back from the brain, so we don't double-count.

      // Threat level follows the BRAIN's own dial label, so the app and the
      // engine can never disagree. Evidence must come from the dial.
      const level = (data.dial_label || "NORMAL").trim().toUpperCase();
      if (level === "CRITICAL" || level === "HIGH RISK") {
        onThreatUpdate("CRITICAL_SOS", score);
      } else if (level === "ELEVATED") {
        onThreatUpdate("ELEVATED", score);
      } else if (level === "CONCERNING") {
        onThreatUpdate("MONITORING", score);
      } else {
        onThreatUpdate("NORMAL", score);
      }
    } catch (err) {
      console.warn("[AudioSafety] Chunk upload failed:", err);
      if (++failStreakRef.current >= 3 && monitoringRef.current) {
        setMonitorStatus("disconnected");
      }
    }
  }, [onThreatUpdate]);

  const floatToWav = useCallback((samples: Float32Array, sampleRate: number): Blob => {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    const writeStr = (offset: number, str: string) => {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    };
    writeStr(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeStr(8, "WAVE");
    writeStr(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(36, "data");
    view.setUint32(40, samples.length * 2, true);
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return new Blob([buffer], { type: "audio/wav" });
  }, []);

  const startMonitoring = useCallback(async () => {
    if (monitoringRef.current) return;
    setMonitorStatus("connecting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ctx = new AudioContext();
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      chunkBufRef.current = [];
      monitoringRef.current = true;
      chunkIdxRef.current = 0;
      failStreakRef.current = 0;
      journeyIdRef.current = new Date().toISOString().replace(/[:.\-T]/g, "").slice(0, 14);

      // A failed session ping is not fatal: chunks will reveal the truth.
      fetch(`${AUDIO_SERVER}/start_session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ journey_id: journeyIdRef.current }),
      }).catch(() => {});
      // This app deliberately does NOT call /toggle_recording: audio is
      // analysed in 3-second chunks and nothing is stored here.

      processor.onaudioprocess = (e) => {
        if (!monitoringRef.current) return;
        const data = new Float32Array(e.inputBuffer.getChannelData(0));
        chunkBufRef.current.push(new Float32Array(data));
        const SLICE = 4;
        const step = Math.max(1, Math.floor(data.length / SLICE));
        for (let s = 0; s + step <= data.length; s += step) {
          let peak = 0;
          for (let i = s; i < s + step; i++) {
            const v = Math.abs(data[i]);
            if (v > peak) peak = v;
          }
          levelsRef.current.push(Math.min(1, peak * 2.2));
        }
        if (levelsRef.current.length > 28) {
          levelsRef.current.splice(0, levelsRef.current.length - 28);
        }
      };

      source.connect(processor);
      processor.connect(ctx.destination);

      timerRef.current = setInterval(() => {
        if (!monitoringRef.current || chunkBufRef.current.length === 0) return;
        const totalLen = chunkBufRef.current.reduce((sum, buf) => sum + buf.length, 0);
        const merged = new Float32Array(totalLen);
        let offset = 0;
        for (const buf of chunkBufRef.current) {
          merged.set(buf, offset);
          offset += buf.length;
        }
        chunkBufRef.current = [];
        const wav = floatToWav(merged, ctx.sampleRate);
        sendChunk(wav, chunkIdxRef.current++);
      }, 3000);

      // Start live transcription. Final utterances are shown to the rider and
      // forwarded to the brain on the next chunk. Restarts itself if the engine
      // auto-stops; silently no-ops where Web Speech is unsupported.
      try {
        const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SR) {
          const rec = new SR();
          rec.continuous = true;
          rec.interimResults = true;
          rec.lang = (import.meta.env.VITE_SPEECH_LANG as string) || "en-US";
          rec.onresult = (ev: any) => {
            for (let i = ev.resultIndex; i < ev.results.length; i++) {
              const res = ev.results[i];
              if (res.isFinal) {
                const txt = String(res[0].transcript || "").trim();
                if (txt) {
                  heardSinceChunkRef.current += " " + txt;
                  setTranscript((prev) => (prev + " " + txt).slice(-400));
                }
              }
            }
          };
          rec.onerror = () => { /* denied / no-speech: acoustics keep running */ };
          rec.onend = () => { if (monitoringRef.current) { try { rec.start(); } catch { /* already running */ } } };
          rec.start();
          recogRef.current = rec;
        }
      } catch { /* unsupported browser: acoustic-only, no words */ }

      setIsMonitoring(true);
      setMonitorStatus("live");
    } catch (err) {
      console.error("[AudioSafety] Failed to start monitoring:", err);
      monitoringRef.current = false;
      setIsMonitoring(false);
      setMonitorStatus("disconnected");
    }
  }, [floatToWav, sendChunk]);

  const stopMonitoring = useCallback(() => {
    monitoringRef.current = false;
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (processorRef.current) { processorRef.current.disconnect(); processorRef.current = null; }
    if (streamRef.current) { streamRef.current.getTracks().forEach((t) => t.stop()); streamRef.current = null; }
    if (recogRef.current) {
      try { recogRef.current.onend = null; recogRef.current.stop(); } catch { /* ignore */ }
      recogRef.current = null;
    }
    heardSinceChunkRef.current = "";
    setTranscript("");

    if (journeyIdRef.current) {
      fetch(`${AUDIO_SERVER}/stop_session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ journey_id: journeyIdRef.current }),
      }).catch(() => {});
    }
    setIsMonitoring(false);
    setMonitorStatus("idle");
    setDistressScore(0);
    setDialLabel("NORMAL");
    failStreakRef.current = 0;
  }, []);

  useEffect(() => {
    return () => { stopMonitoring(); };
  }, [stopMonitoring]);

  const getAudioLevels = useCallback(() => levelsRef.current, []);

  return { isMonitoring, monitorStatus, distressScore, dialLabel, lastResult, transcript, startMonitoring, stopMonitoring, getAudioLevels };
}
