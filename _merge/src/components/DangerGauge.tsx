import React from "react";
import { Maximize2 } from "lucide-react";

/**
 * The Abhi AI risk dial as a calm semicircle. Colour carries meaning so the
 * rider reads status in a glance instead of reading sentences.
 * score: 0..100 (percent of the engine's 0..13 dial).
 * onClick: opens the full AI dashboard - the dial is the entry point (the v1
 * pattern), so it never needs a separate button stealing space beside it.
 */
export function DangerGauge({
  score,
  label,
  size = 190,
  onClick,
}: {
  score: number;
  label: string;
  size?: number;
  onClick?: () => void;
}) {
  const s = Math.max(0, Math.min(100, score));
  const stroke = 14;
  const r = (size - stroke) / 2 - 10;
  const cx = size / 2;
  const cy = size / 2 + r / 1.8;
  const arcLen = Math.PI * r; // semicircle length
  const filled = (s / 100) * arcLen;

  let color = "#16a34a";
  if (s >= 70) color = "#e11d48";
  else if (s >= 38) color = "#d97706";
  else if (s > 8) color = "#0b5fff";

  const a = Math.PI - (s / 100) * Math.PI; // 180deg -> 0deg
  const nx = cx + r * Math.cos(a);
  const ny = cy - r * Math.sin(a);

  return (
    <div
      className="gauge-wrap"
      style={{ width: size, cursor: onClick ? "pointer" : "default" }}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      title={onClick ? "Open the full AI dashboard" : undefined}
    >
      {onClick && (
        <span className="gauge-expand" aria-hidden>
          <Maximize2 size={13} />
        </span>
      )}
      <svg width={size} height={cy + 14} viewBox={`0 0 ${size} ${cy + 14}`}>
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="#e6ebf3"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${arcLen}`}
          style={{ transition: "stroke-dasharray 0.7s ease, stroke 0.7s ease" }}
        />
        {s > 2 && <circle cx={nx} cy={ny} r={7} fill="#fff" stroke={color} strokeWidth={3.5} />}
      </svg>
      <div className="gauge-num" style={{ color }}>{Math.round(s)}</div>
      <div className="gauge-cap">risk dial · {label}</div>
      {onClick && <div className="gauge-hint">tap for AI detail</div>}
    </div>
  );
}
