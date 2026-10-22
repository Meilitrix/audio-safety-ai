import React from "react";

/**
 * Dependency-free route preview: normalises [lat,lng] geometry into a 100x50
 * viewBox polyline. No tile provider, no API key - honest about shape only.
 * `progress` (0..1) paints the travelled part in the live colour.
 */
export function RouteMap({
  geometry,
  progress = 0,
  height = 110,
}: {
  geometry: [number, number][];
  progress?: number;
  height?: number;
}) {
  if (!geometry || geometry.length < 2) return null;

  const lats = geometry.map((g) => g[0]);
  const lngs = geometry.map((g) => g[1]);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
  const spanLat = Math.max(maxLat - minLat, 1e-6);
  const spanLng = Math.max(maxLng - minLng, 1e-6);
  const PAD = 8;

  const pts = geometry.map(([la, ln]) => {
    const x = PAD + ((ln - minLng) / spanLng) * (100 - PAD * 2);
    // SVG y is flipped: northern latitudes sit higher
    const y = 50 - PAD - ((la - minLat) / spanLat) * (50 - PAD * 2);
    return [x, y] as [number, number];
  });

  const full = pts.map((p) => `${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" ");
  const uptoIdx = Math.max(1, Math.min(pts.length - 1, Math.round(progress * (pts.length - 1))));
  const done = pts.slice(0, uptoIdx + 1).map((p) => `${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" ");
  const car = pts[uptoIdx];
  const start = pts[0];
  const end = pts[pts.length - 1];

  return (
    <svg className="routemap" viewBox="0 0 100 50" preserveAspectRatio="none" style={{ height }}>
      <polyline points={full} />
      {progress > 0 && <polyline className="live" points={done} />}
      <circle cx={start[0]} cy={start[1]} r={2.6} fill="#16a34a" stroke="#fff" strokeWidth="1" />
      <circle cx={end[0]} cy={end[1]} r={2.6} fill="#e11d48" stroke="#fff" strokeWidth="1" />
      {progress > 0 && <circle cx={car[0]} cy={car[1]} r={3.2} fill="#0bb8c2" stroke="#fff" strokeWidth="1.4" />}
    </svg>
  );
}
