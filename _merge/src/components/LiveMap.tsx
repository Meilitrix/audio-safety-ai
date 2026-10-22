import React, { useEffect, useRef, useState, useMemo } from "react";
import L from "leaflet";
import {
  MapPin,
  Car,
  Clock,
  Gauge,
  RotateCcw,
  Layers,
  ZoomIn,
  ZoomOut,
  Shield,
  Navigation,
} from "lucide-react";
import { LocationItem, RideStatus, ThreatLevel, DriverProfile, RouteOption } from "../types";

interface LiveMapProps {
  pickup: LocationItem;
  // On the mobile flow the rider picks the pickup first: the map has to work
  // before a dropoff exists (merge 2026-10-22).
  dropoff: LocationItem | null;
  rideStatus: RideStatus;
  threatLevel: ThreatLevel;
  tripProgress: number;
  selectedDriver?: DriverProfile;
  isAudioMonitoring: boolean;
  routes: RouteOption[];
  selectedRouteId: string | null;
  deviationPosition: { lat: number; lng: number } | null;
  // Trip screen passes this to shrink the map so the SOS control fits on one
  // screen instead of pushing the rider into a scroll.
  compact?: boolean;
}

// Free tile sources - no API key, no watermark:
// Street = Esri World Street Map (renders place names in ENGLISH/Latin script;
// the raw OSM tiles were dropped because they stamp Urdu over Pakistan, which
// locals found unreadable). Esri imagery = satellite. CARTO basemaps were also
// dropped: they now stamp "API KEY REQUIRED" over tiles.
type MapTheme = "osm" | "satellite";
const TILE_URLS: Record<MapTheme, string> = {
  osm: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
  satellite: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
};

export const LiveMap: React.FC<LiveMapProps> = ({
  pickup,
  dropoff,
  rideStatus,
  threatLevel,
  tripProgress,
  selectedDriver,
  isAudioMonitoring,
  routes,
  selectedRouteId,
  deviationPosition,
  compact,
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const carMarkerRef = useRef<L.Marker | null>(null);
  const routePolylinesRef = useRef<L.Polyline[]>([]);
  const pickupMarkerRef = useRef<L.Marker | null>(null);
  const dropoffMarkerRef = useRef<L.Marker | null>(null);
  const deviationMarkerRef = useRef<L.Marker | null>(null);
  const selectFocusRef = useRef<{ pKey: string; dKey: string } | null>(null);
  // Guards fitBounds to real journey changes (see the polyline effect).
  const fittedKeyRef = useRef<string>("");

  const [mapTheme, setMapTheme] = useState<MapTheme>("osm");

  // Use selected route geometry or fallback to straight line
  const activeRoute = useMemo(() => {
    if (routes.length === 0) return null;
    return routes.find((r) => r.id === selectedRouteId) || routes[0];
  }, [routes, selectedRouteId]);

  const routeCoordinates = useMemo<[number, number][]>(() => {
    if (activeRoute && activeRoute.geometry.length > 0) return activeRoute.geometry;
    // No fake straight line between pins any more: until a real OSRM route
    // arrives, the car simply waits at the pickup point.
    return [
      [pickup.lat, pickup.lng],
      [pickup.lat, pickup.lng],
    ];
  }, [activeRoute, pickup.lat, pickup.lng, dropoff?.lat, dropoff?.lng]);

  // Interpolate along route according to progress percentage
  const getPositionAlongRoute = (pct: number) => {
    const clamped = Math.max(0, Math.min(100, pct));
    const totalSegments = routeCoordinates.length - 1;
    const progressPerSegment = 100 / totalSegments;
    const segmentIndex = Math.min(Math.floor(clamped / progressPerSegment), totalSegments - 1);
    const segmentProgress = (clamped % progressPerSegment) / progressPerSegment;

    const p1 = routeCoordinates[segmentIndex];
    const p2 = routeCoordinates[segmentIndex + 1] || p1;

    const lat = p1[0] + (p2[0] - p1[0]) * segmentProgress;
    const lng = p1[1] + (p2[1] - p1[1]) * segmentProgress;

    const dLat = p2[0] - p1[0];
    const dLng = p2[1] - p1[1];
    const angleDeg = (Math.atan2(dLng, dLat) * 180) / Math.PI;

    return { lat, lng, angle: angleDeg };
  };

  const currentCarPos = getPositionAlongRoute(
    rideStatus === "IN_TRIP" ? tripProgress : rideStatus === "DRIVER_ASSIGNED" ? 15 : 0
  );



  // While the rider is picking places, glide the map to whichever pin was
  // just chosen. The cruising "nearby cars" layer was removed on 2026-10-22 -
  // it sat on top of the road geometry and made the route hard to read. Once
  // both pins are set the rider presses See Routes, and the route-fit effect
  // below frames the whole path; they can zoom in from there themselves.
  useEffect(() => {
    if (rideStatus !== "SELECTING_DESTINATION" || !mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    const pKey = pickup.lat + "," + pickup.lng;
    const dKey = dropoff ? dropoff.lat + "," + dropoff.lng : "";
    const prev = selectFocusRef.current;
    selectFocusRef.current = { pKey, dKey };
    if (!prev) return;
    if (prev.pKey !== pKey) map.flyTo([pickup.lat, pickup.lng], Math.max(map.getZoom(), 15), { duration: 0.6 });
    if (dropoff && prev.dKey !== dKey) map.flyTo([dropoff.lat, dropoff.lng], Math.max(map.getZoom(), 15), { duration: 0.6 });
  }, [pickup.lat, pickup.lng, dropoff?.lat, dropoff?.lng, rideStatus]);

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const centerLat = (pickup.lat + (dropoff?.lat ?? pickup.lat)) / 2;
    const centerLng = (pickup.lng + (dropoff?.lng ?? pickup.lng)) / 2;

    const map = L.map(mapContainerRef.current, {
      center: [centerLat, centerLng],
      zoom: 13,
      zoomControl: false,
      attributionControl: true,
    });

    mapInstanceRef.current = map;

    const tileLayer = L.tileLayer(TILE_URLS[mapTheme], {
      maxZoom: 19,
      subdomains: "abc",
      attribution: '&copy; Esri, HERE, Garmin, OpenStreetMap contributors',
    }).addTo(map);
    tileLayerRef.current = tileLayer;

    return () => {
      // StrictMode/dev remounts build a NEW map instance. Any marker or line
      // still held in the refs belongs to the destroyed one - setLatLng/setIcon
      // on it silently updates nothing, which is how the car marker vanished
      // from the trip screen. Drop every handle so the effects re-add them.
      routePolylinesRef.current.forEach((p) => p.remove());
      routePolylinesRef.current = [];
      carMarkerRef.current = null;
      pickupMarkerRef.current = null;
      dropoffMarkerRef.current = null;
      deviationMarkerRef.current = null;
      fittedKeyRef.current = "";
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update tile layer on theme change
  useEffect(() => {
    if (!mapInstanceRef.current || !tileLayerRef.current) return;
    tileLayerRef.current.setUrl(TILE_URLS[mapTheme]);
  }, [mapTheme]);

  // Render route polylines (selected = solid, alternatives = faded)
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    // Clear old route lines
    routePolylinesRef.current.forEach((p) => p.remove());
    routePolylinesRef.current = [];

        // Paths are back (2026-10-21) but structurally honest: App only ever
    // passes routes that belong to the CURRENT pickup/dropoff pair, so a
    // line can never depict someone else's journey. No data = no lines,
    // just the two pins framed in view.
    if (routes.length === 0) {
      if (pickup && dropoff && rideStatus !== "SELECTING_DESTINATION") {
        map.fitBounds(
          [[pickup.lat, pickup.lng], [dropoff.lat, dropoff.lng]] as L.LatLngExpression[],
          { padding: [60, 60] }
        );
      }
      return;
    }

    // Draw alternative routes first (faded)
    routes.forEach((route) => {
      const isSelected = route.id === selectedRouteId || (!selectedRouteId && route.id === routes[0].id);
      if (isSelected) return; // draw selected last so it's on top

      const line = L.polyline(route.geometry, {
        color: route.color || "#475569",
        weight: 4,
        opacity: 0.4,
        dashArray: "8, 8",
      }).addTo(map);
      routePolylinesRef.current.push(line);
    });

    // Draw selected route (solid, colored by threat)
    const selected = routes.find((r) => r.id === selectedRouteId) || routes[0];
    const routeColor =
      threatLevel === "CRITICAL_SOS" ? "#ef4444" : threatLevel === "ELEVATED" ? "#f59e0b" : "#0284c7";

    const selectedLine = L.polyline(selected.geometry, {
      color: routeColor,
      weight: 5,
      opacity: 0.9,
      lineCap: "round",
      lineJoin: "round",
    }).addTo(map);
    routePolylinesRef.current.push(selectedLine);

    // Fit bounds - but only when the framed journey actually changed. The
    // parent re-creates the routes array on every render (trip tick = every
    // 2s), and an unconditional fitBounds kept yanking the zoom back out the
    // moment the rider zoomed in to study the road.
    const fitKey = `${selected.id}|${pickup.lat},${pickup.lng}|${dropoff?.lat ?? ""},${dropoff?.lng ?? ""}`;
    if (fittedKeyRef.current !== fitKey) {
      fittedKeyRef.current = fitKey;
      map.fitBounds(selectedLine.getBounds(), { padding: [50, 50] });
    }
  }, [routes, selectedRouteId, threatLevel, rideStatus, pickup?.lat, pickup?.lng, dropoff?.lat, dropoff?.lng]);

  // Pickup / Dropoff markers
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    pickupMarkerRef.current?.remove();
    const pickupHtml = `
      <div style="display:flex;flex-direction:column;align-items:center;">
        <div style="background:#059669;color:white;font-size:10px;font-weight:800;padding:2px 8px;border-radius:6px;border:1.5px solid white;box-shadow:0 4px 6px -1px rgba(0,0,0,0.5);white-space:nowrap;margin-bottom:2px;">
          PICKUP: ${pickup.title.split(",")[0]}
        </div>
        <div style="width:16px;height:16px;border-radius:50%;background:#10b981;border:3px solid white;box-shadow:0 0 10px #10b981;"></div>
      </div>`;
    pickupMarkerRef.current = L.marker([pickup.lat, pickup.lng], {
      icon: L.divIcon({ className: "custom-pickup-pin", html: pickupHtml, iconSize: [120, 36], iconAnchor: [60, 36] }),
    }).addTo(map);

    dropoffMarkerRef.current?.remove();
    dropoffMarkerRef.current = null;
    if (dropoff) {
    const dropoffHtml = `
      <div style="display:flex;flex-direction:column;align-items:center;">
        <div style="background:#dc2626;color:white;font-size:10px;font-weight:800;padding:2px 8px;border-radius:6px;border:1.5px solid white;box-shadow:0 4px 6px -1px rgba(0,0,0,0.5);white-space:nowrap;margin-bottom:2px;">
          DROPOFF: ${dropoff.title.split(",")[0]}
        </div>
        <div style="width:16px;height:16px;border-radius:50%;background:#ef4444;border:3px solid white;box-shadow:0 0 10px #ef4444;"></div>
      </div>`;
    dropoffMarkerRef.current = L.marker([dropoff.lat, dropoff.lng], {
      icon: L.divIcon({ className: "custom-dropoff-pin", html: dropoffHtml, iconSize: [120, 36], iconAnchor: [60, 36] }),
    }).addTo(map);
    }
  }, [pickup, dropoff]);



  // Active car marker
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    if (rideStatus === "IN_TRIP" || rideStatus === "DRIVER_ASSIGNED") {
      const isFem = selectedDriver?.isFemaleDriver;
      const isCritical = threatLevel === "CRITICAL_SOS";
      // Ring colour: red only in real danger, pink for the Khwateen fleet, brand
      // blue otherwise. The marker itself is a white avatar showing the driver's
      // initial - not the old solid colour "blob" the rider disliked.
      const ring = isCritical ? "#ef4444" : isFem ? "#e11d48" : "#0284c7";
      const initial = (String(selectedDriver?.name || "?").trim().charAt(0) || "•").toUpperCase();

      const carHtml = `
        <div style="position:relative;display:flex;align-items:center;justify-content:center;width:44px;height:44px;">
          ${isCritical ? `<div style="position:absolute;width:44px;height:44px;border-radius:50%;background:rgba(239,68,68,0.4);animation:ping 1.5s infinite;"></div>` : ""}
          <div style="width:36px;height:36px;border-radius:50%;background:#fff;border:3px solid ${ring};display:flex;align-items:center;justify-content:center;box-shadow:0 3px 10px rgba(0,0,0,0.35);z-index:10;">
            <span style="font:800 17px/1 system-ui,-apple-system,Segoe UI,sans-serif;color:${ring};">${initial}</span>
          </div>
        </div>`;

      const carIcon = L.divIcon({ className: "active-car-icon", html: carHtml, iconSize: [44, 44], iconAnchor: [22, 22] });

      if (!carMarkerRef.current) {
        carMarkerRef.current = L.marker([currentCarPos.lat, currentCarPos.lng], { icon: carIcon, zIndexOffset: 1000 }).addTo(map);
      } else {
        carMarkerRef.current.setLatLng([currentCarPos.lat, currentCarPos.lng]);
        carMarkerRef.current.setIcon(carIcon);
      }

      // No auto-pan while riding: the rider owns the view now. The recenter
      // button below the zoom controls jumps back to the car on demand.
    } else {
      carMarkerRef.current?.remove();
      carMarkerRef.current = null;
    }
  }, [currentCarPos.lat, currentCarPos.lng, currentCarPos.angle, rideStatus, threatLevel, selectedDriver]);

  // Deviation marker
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    deviationMarkerRef.current?.remove();
    deviationMarkerRef.current = null;

    if (deviationPosition) {
      const devHtml = `
        <div style="width:20px;height:20px;border-radius:50%;background:#f59e0b;border:3px solid white;box-shadow:0 0 12px #f59e0b;animation:pulse 1s infinite;"></div>`;
      deviationMarkerRef.current = L.marker([deviationPosition.lat, deviationPosition.lng], {
        icon: L.divIcon({ className: "deviation-marker", html: devHtml, iconSize: [20, 20], iconAnchor: [10, 10] }),
      }).addTo(map);
    }
  }, [deviationPosition]);

  // Recenter
  const handleRecenter = () => {
    if (!mapInstanceRef.current || !routePolylinesRef.current.length) return;
    if (rideStatus === "IN_TRIP") {
      mapInstanceRef.current.setView([currentCarPos.lat, currentCarPos.lng], 15);
    } else {
      const line = routePolylinesRef.current[routePolylinesRef.current.length - 1];
      if (line) mapInstanceRef.current.fitBounds(line.getBounds(), { padding: [50, 50] });
    }
  };

  // HUD stats
  const routeDist = activeRoute?.distanceKm ?? 7.8;
  const remainingKm = Math.max(0.3, Number((routeDist * (1 - tripProgress / 100)).toFixed(1)));
  const remainingMinutes = Math.max(1, Math.ceil((activeRoute?.durationMin ?? 15) * (1 - tripProgress / 100)));
  // Average speed derived from this route's real distance and drive time.
  // Labelled "avg" so nobody reads it as a GPS-measured speed - the car
  // marker is an animation, so an instantaneous speed would be a lie.
  const durMin = Math.max(1, activeRoute?.durationMin ?? 15);
  const avgKmH = rideStatus === "IN_TRIP" ? Math.round((routeDist / durMin) * 60) : 0;

  return (
    <div className="relative w-full h-[300px] sm:h-[350px] lg:h-[400px] rounded-2xl overflow-hidden border border-slate-200 shadow-md select-none bg-white" style={compact ? { height: 196 } : undefined}>
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Top HUD - light glass pills (see .map-hud in index.css); the dark
          slate styling was the v1 app's theme and vanished in the merge. */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-10">
        <div className="map-hud px-3.5 py-2 text-xs flex items-center gap-3 pointer-events-auto">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-black uppercase tracking-wider text-[11px]">
              {pickup.city}
            </span>
          </div>
          <div className="hud-sep" />
          <div className="flex items-center gap-1.5 hud-dim font-mono text-[11px]">
            <Clock className="w-3.5 h-3.5 text-teal-600" />
            <span>
              <strong>{remainingMinutes} min</strong> ({remainingKm} km)
            </span>
          </div>
          {rideStatus === "IN_TRIP" && (
            <>
              <div className="hud-sep" />
              <div className="flex items-center gap-1 hud-dim font-mono text-[11px]">
                <Gauge className="w-3.5 h-3.5 text-teal-600" />
                <span>{avgKmH} km/h avg</span>
              </div>
            </>
          )}
        </div>

        <div className="map-hud px-3 py-1.5 flex items-center gap-2 text-xs pointer-events-auto">
          <Shield className="w-4 h-4 text-emerald-600" />
          <span className="font-bold text-[11px]">Police 15</span>
        </div>
      </div>

      {/* Map controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2 z-10">
        <div className="map-hud p-1 flex flex-col gap-1">
          <button
            onClick={() => setMapTheme((c) => (c === "osm" ? "satellite" : "osm"))}
            title="Map style"
          >
            <Layers className="w-4 h-4" />
          </button>
          <button onClick={handleRecenter} title="Recenter">
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
        <div className="map-hud p-1 flex flex-col gap-1">
          <button onClick={() => mapInstanceRef.current?.zoomIn()}>
            <ZoomIn className="w-4 h-4" />
          </button>
          <button onClick={() => mapInstanceRef.current?.zoomOut()}>
            <ZoomOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
