export interface LngLat {
  lat: number;
  lng: number;
}

/**
 * Point along a [lat,lng] polyline at progress 0..1, by cumulative segment
 * length. Deterministic: the demo car is exactly where the route says it is.
 */
export function interpolateRoute(geometry: [number, number][], progress: number): LngLat {
  if (!geometry || geometry.length === 0) return { lat: 33.6844, lng: 73.0479 };
  if (geometry.length === 1) return { lat: geometry[0][0], lng: geometry[0][1] };
  const p = Math.max(0, Math.min(1, progress));

  const segLens: number[] = [];
  let total = 0;
  for (let i = 0; i < geometry.length - 1; i++) {
    const dLat = geometry[i + 1][0] - geometry[i][0];
    const dLng = geometry[i + 1][1] - geometry[i][1];
    const d = Math.hypot(dLat, dLng);
    segLens.push(d);
    total += d;
  }
  let target = total * p;
  for (let i = 0; i < segLens.length; i++) {
    if (target <= segLens[i] || i === segLens.length - 1) {
      const t = segLens[i] === 0 ? 0 : Math.min(1, target / segLens[i]);
      return {
        lat: geometry[i][0] + (geometry[i + 1][0] - geometry[i][0]) * t,
        lng: geometry[i][1] + (geometry[i + 1][1] - geometry[i][1]) * t,
      };
    }
    target -= segLens[i];
  }
  return { lat: geometry[geometry.length - 1][0], lng: geometry[geometry.length - 1][1] };
}

/** A Google Maps link is just a URL built from coordinates - free, no API. */
export function mapsLinkFor(pos: LngLat): string {
  return `https://maps.google.com/?q=${pos.lat.toFixed(6)},${pos.lng.toFixed(6)}`;
}

export function loadJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (raw) return JSON.parse(raw) as T;
  } catch {
    /* ignore corrupt storage */
  }
  return fallback;
}

export function saveJSON(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore quota errors */
  }
}
