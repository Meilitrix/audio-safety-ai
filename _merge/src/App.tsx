import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  RideStatus, ThreatLevel, LocationItem, DriverProfile, IncidentReport,
  EmergencyContact, PaymentMethod, AIFeedbackRecord, RouteOption,
} from "./types";
import { POPULAR_LOCATIONS, AVAILABLE_PAKISTANI_DRIVERS } from "./data/rideData";
import { useAudioSafety } from "./hooks/useAudioSafety";
import { LiveMap } from "./components/LiveMap";
import { Car, Radar } from "lucide-react";
import { DangerGauge } from "./components/DangerGauge";
import { BottomSheet, Wave } from "./components/Sheet";
import { PaySheet, FeedbackSheet, DebriefSheet } from "./components/RideEndSheets";
import { interpolateRoute, mapsLinkFor, loadJSON, saveJSON, LngLat } from "./lib/ride";

const INITIAL_EMERGENCY_CONTACTS: EmergencyContact[] = [];

const SAFETY_CHECK_SECONDS = 20;

// The AI dashboard is the Python brain's own board on port 5004. Host derives
// from the page so a phone on the same Wi-Fi sees the same live data.
const BRAIN_HOST = (import.meta as any).env?.VITE_AUDIO_HOST || window.location.hostname || "localhost";

// Dev shortcut: ?stage=home|routes|drivers|assigned|trip|end
const STAGE_URL_MAP: Record<string, RideStatus> = {
  home: "SELECTING_DESTINATION",
  routes: "ROUTE_SELECTION",
  drivers: "CHOOSING_DRIVER",
  assigned: "DRIVER_ASSIGNED",
  trip: "IN_TRIP",
  end: "TRIP_COMPLETED",
};

export default function App() {
  const initialStage =
    STAGE_URL_MAP[new URLSearchParams(window.location.search).get("stage") || ""] || "SELECTING_DESTINATION";

  // ── Flow state ───────────────────────────────────────────────────
  const [stage, setStage] = useState<RideStatus>(initialStage);
  const [pickup, setPickup] = useState<LocationItem>(POPULAR_LOCATIONS[0]);
  const [dropoff, setDropoff] = useState<LocationItem | null>(null);
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [routesLoading, setRoutesLoading] = useState(false);
  const [routesError, setRoutesError] = useState(false);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [drivers, setDrivers] = useState<DriverProfile[]>([]);
  const [selectedDriver, setSelectedDriver] = useState<DriverProfile | null>(null);
  const [tripProgress, setTripProgress] = useState(0);

  // ── Rider profile + contacts (persisted) ─────────────────────────
  const [riderName, setRiderName] = useState(() => loadJSON<{ name: string }>("abhi_rider", { name: initialStage !== "SELECTING_DESTINATION" ? "Demo Rider" : "" }).name);
  const [riderDraft, setRiderDraft] = useState("");
  const [onboarded, setOnboarded] = useState(() => Boolean(loadJSON<{ name: string }>("abhi_rider", { name: "" }).name) || initialStage !== "SELECTING_DESTINATION");
  const [contacts, setContacts] = useState<EmergencyContact[]>(() => loadJSON("abhi_emergency_contacts", INITIAL_EMERGENCY_CONTACTS));
  const [isContactsOpen, setIsContactsOpen] = useState(false);
  const [isDashOpen, setIsDashOpen] = useState(false);
  const [permOpen, setPermOpen] = useState(false);
  const [payChoice, setPayChoice] = useState<{ method: PaymentMethod; total: number } | null>(null);

  // ── Safety state ─────────────────────────────────────────────────
  const [threatLevel, setThreatLevel] = useState<ThreatLevel>("NORMAL");
  const [distressScore, setDistressScore] = useState(0);
  const [livePos, setLivePos] = useState<LngLat | null>(null);
  const [gpsLabel, setGpsLabel] = useState("acquiring GPS…");
  const [sosSheet, setSosSheet] = useState<"closed" | "prompt" | "results">("closed");
  const [sosReason, setSosReason] = useState("");
  const [sosCountdown, setSosCountdown] = useState(SAFETY_CHECK_SECONDS);
  const [incident, setIncident] = useState<IncidentReport | null>(null);
  const [dispatchResult, setDispatchResult] = useState<any>(null);
  const [deviationOn, setDeviationOn] = useState(false);
  const [dispatchMode, setDispatchMode] = useState<"live" | "mock" | null>(null);
  const autoSosArmedRef = useRef(false);
  const autoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Ride end state ───────────────────────────────────────────────
  const [endStep, setEndStep] = useState<"pay" | "feedback" | "debrief">("pay");
  const [, setFeedbackLog] = useState<AIFeedbackRecord[]>(() => loadJSON("abhi_feedback_log", [] as AIFeedbackRecord[]));

  const handleThreatUpdate = useCallback((t: string, s: number) => {
    setThreatLevel(t as ThreatLevel);
    setDistressScore(s);
  }, []);
  const audio = useAudioSafety(handleThreatUpdate);

  const activeRoute = routes.find((r) => r.id === selectedRouteId) || null;
  const tripMinutes = activeRoute?.durationMin || 12;

  // ── Routes: fetch with real loading + error + retry (no dead ends) ─
  const fetchRoutes = useCallback(async () => {
    if (!dropoff) return;
    setRoutesLoading(true);
    setRoutesError(false);
    setRoutes([]);
    try {
      const params = new URLSearchParams({
        pickup_lat: String(pickup.lat), pickup_lng: String(pickup.lng),
        drop_lat: String(dropoff.lat), drop_lng: String(dropoff.lng),
      });
      const res = await fetch(`/api/routes?${params}`);
      const data = await res.json();
      if (res.ok && data.success && data.routes?.length > 0) {
        setRoutes(data.routes);
        setSelectedRouteId(data.routes[0].id);
        setRoutesLoading(false);
        return;
      }
      throw new Error(data.error || "No routes returned");
    } catch (err) {
      console.warn("Route fetch failed:", err);
      // Offline shape: this is NOT a road. It is a straight line between the two
      // pins so the demo can continue, labelled as such and flagged by the error
      // banner. It carries no safety score, because nothing here measured safety.
      const geom: [number, number][] = [];
      for (let t = 0; t <= 1.0001; t += 0.05) {
        geom.push([
          pickup.lat + (dropoff.lat - pickup.lat) * t,
          pickup.lng + (dropoff.lng - pickup.lng) * t,
        ]);
      }
      const km =
        (Math.hypot(dropoff.lat - pickup.lat, dropoff.lng - pickup.lng) * 111).toFixed(1);
      setRoutes([{
        id: "route_fallback", geometry: geom, distanceKm: Number(km),
        durationMin: Math.max(6, Math.round(Number(km) * 2.4)),
        safetyLevel: "unrated", safetyScore: null, summary: "Straight line (no road data)",
      }]);
      setSelectedRouteId("route_fallback");
      setRoutesLoading(false);
      setRoutesError(true);
    }
  }, [pickup, dropoff]);

  // ── Which dispatch channel is actually live? (email live/mock) ───
  useEffect(() => {
    fetch("/api/dispatch-status")
      .then((r) => r.json())
      .then((d) => setDispatchMode(d.mode === "live" ? "live" : "mock"))
      .catch(() => setDispatchMode("mock"));
  }, []);

  // ── ?stage= deep links (rehearsal tool) ───────────────────────────
  // Jumping past the destination screen used to land on empty stages: no
  // dropoff, no routes, no driver. Seed the demo pair so every deep link
  // opens a screen with real content behind it.
  useEffect(() => {
    if (initialStage === "SELECTING_DESTINATION") return;
    setDropoff(POPULAR_LOCATIONS[1]);
    if (initialStage === "CHOOSING_DRIVER") setDrivers(AVAILABLE_PAKISTANI_DRIVERS);
    else setSelectedDriver(AVAILABLE_PAKISTANI_DRIVERS[0]);
  }, [initialStage]);
  // Once the seeded dropoff lands in state, fetchRoutes sees it and pulls
  // the real OSRM geometry for the route/assigned/trip screens.
  useEffect(() => {
    if (initialStage !== "SELECTING_DESTINATION" && dropoff && routes.length === 0) void fetchRoutes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dropoff]);

  // ── Driver search: deterministic, no Math.random ─────────────────
  useEffect(() => {
    if (stage === "SEARCHING_DRIVER") {
      const t = setTimeout(() => {
        setDrivers(AVAILABLE_PAKISTANI_DRIVERS);
        setStage("CHOOSING_DRIVER");
      }, 1800);
      return () => clearTimeout(t);
    }
  }, [stage]);

  // ── Trip ticker: real elapsed time vs the OSRM duration ──────────
  useEffect(() => {
    if (stage !== "IN_TRIP") return;
    const started = Date.now();
    const id = setInterval(() => {
      const frac = (Date.now() - started) / (tripMinutes * 60_000);
      setTripProgress(Math.min(1, 0.04 + frac));
    }, 2000);
    return () => clearInterval(id);
  }, [stage, tripMinutes]);

  // ── Live GPS: real device fix when granted, route position otherwise ─
  useEffect(() => {
    if (stage !== "IN_TRIP") return;
    let stopWatch = () => {};
    if ("geolocation" in navigator) {
      const id = navigator.geolocation.watchPosition(
        (p) => {
          setLivePos({ lat: p.coords.latitude, lng: p.coords.longitude });
          setGpsLabel(`GPS live ±${Math.round(p.coords.accuracy)} m`);
        },
        () => setGpsLabel("GPS unavailable - using route position"),
        { enableHighAccuracy: true, maximumAge: 5000 }
      );
      stopWatch = () => navigator.geolocation.clearWatch(id);
    } else {
      setGpsLabel("GPS unsupported - using route position");
    }
    return stopWatch;
  }, [stage]);

  const routePos = activeRoute ? interpolateRoute(activeRoute.geometry, tripProgress) : { lat: pickup.lat, lng: pickup.lng };
  const currentPos: LngLat = livePos ?? routePos;

  // ── Route deviation: real /api/check-deviation against live position ─
  useEffect(() => {
    if (stage !== "IN_TRIP" || !activeRoute) return;
    const id = setInterval(async () => {
      try {
        const res = await fetch("/api/check-deviation", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lat: currentPos.lat, lng: currentPos.lng, routeGeometry: activeRoute.geometry }),
        });
        const d = await res.json();
        setDeviationOn(Boolean(d.isDeviation));
      } catch {
        /* deviation check is best-effort */
      }
    }, 15000);
    return () => clearInterval(id);
  }, [stage, activeRoute, currentPos.lat, currentPos.lng]);

  // ── Auto-SOS: sustained CRITICAL arms a safety check (never silent) ─
  useEffect(() => {
    if (stage !== "IN_TRIP") return;
    if (threatLevel === "CRITICAL_SOS" && distressScore >= 70 && !autoSosArmedRef.current) {
      autoSosArmedRef.current = true;
      autoTimerRef.current = setTimeout(() => openSosPrompt("Abhi AI hears sounds that may mean you are in danger."), 5000);
    }
    if (threatLevel !== "CRITICAL_SOS" && distressScore < 40) {
      autoSosArmedRef.current = false;
      if (autoTimerRef.current) { clearTimeout(autoTimerRef.current); autoTimerRef.current = null; }
    }
  }, [threatLevel, distressScore, stage]);

  const openSosPrompt = (reason: string) => {
    setSosReason(reason);
    setSosCountdown(SAFETY_CHECK_SECONDS);
    setSosSheet("prompt");
    if (countdownRef.current) clearInterval(countdownRef.current);
    countdownRef.current = setInterval(() => {
      setSosCountdown((n) => {
        if (n <= 1) {
          if (countdownRef.current) { clearInterval(countdownRef.current); countdownRef.current = null; }
          fireSOS();
          return 0;
        }
        return n - 1;
      });
    }, 1000);
  };

  const stopCountdown = () => {
    if (countdownRef.current) { clearInterval(countdownRef.current); countdownRef.current = null; }
  };

  // "I am safe" DE-ESCALATES - it never wipes the escalation history.
  const handleImSafe = () => {
    stopCountdown();
    setSosSheet("closed");
    setThreatLevel("ELEVATED");
    setDistressScore((s) => Math.min(s, 35));
    autoSosArmedRef.current = false;
  };

  const fireSOS = async () => {
    if (sosSheet === "results") return; // already dispatched this incident
    stopCountdown();
    const link = mapsLinkFor(currentPos);
    const report: IncidentReport = {
      incidentId: `INC-PAK-${Date.now().toString().slice(-6)}-${Math.floor(100 + Math.random() * 900)}`,
      timestamp: new Date().toLocaleTimeString(),
      isoTime: new Date().toISOString(),
      severity: "CRITICAL_SOS",
      category: threatLevel === "CRITICAL_SOS" ? "VOICE_DISTRESS_SCREAM" : "DIRECT_DISTRESS_KEYWORD",
      summary: sosReason || "Rider triggered SOS.",
      detectedKeywords: [],
      transcriptSnippet: audio.transcript.slice(-200),
      riderTone: "Unknown",
      driverTone: "Unknown",
      backgroundAcoustic: audio.dialLabel,
      distressScore: Math.round(distressScore),
      // LIVE position - the old build wrongly sent the pickup address here.
      gpsCoordinates: { lat: currentPos.lat, lng: currentPos.lng, address: gpsLabel },
      vehicleDetails: {
        driverName: selectedDriver?.name || "Unknown",
        vehicle: selectedDriver ? `${selectedDriver.carColor} ${selectedDriver.carModel}` : "Unknown",
        plate: selectedDriver?.licensePlate || "-",
        riderName: riderName || "Rider",
        driverPhone: selectedDriver?.phone,
      },
      emergencyDispatched: true,
      actionsTaken: [],
    };
    setIncident(report);
    try {
      const res = await fetch("/api/emergency/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          incidentId: report.incidentId,
          riderName: report.vehicleDetails.riderName,
          driverName: report.vehicleDetails.driverName,
          vehiclePlate: report.vehicleDetails.plate,
          reason: report.summary,
          location: report.gpsCoordinates,
          // The auto-notify flags finally DO something: only opted-in contacts go out.
          contactNumbers: contacts.filter((c) => c.autoSmsGpsOnSos || c.autoCallOnSos).map((c) => c.phone),
          contactEmails: contacts.filter((c) => (c.autoSmsGpsOnSos || c.autoCallOnSos) && c.email).map((c) => c.email!),
        }),
      });
      setDispatchResult(await res.json());
    } catch (err) {
      setDispatchResult({ success: false, mapsLink: link, results: [], error: String(err) });
    }
    setSosSheet("results");
  };

  const manualSOS = () => {
    setSosReason("You pressed the SOS button.");
    fireSOS();
  };

  // Demo helper: drives the SAME code path the real dial would drive.
  const simulateDanger = () => {
    setThreatLevel("CRITICAL_SOS");
    setDistressScore(96);
    openSosPrompt("DEMO: sustained high risk on the dial (simulated).");
  };

  // ── Ride end ─────────────────────────────────────────────────────
  const arriveRide = () => {
    audio.stopMonitoring();
    stopCountdown();
    if (autoTimerRef.current) { clearTimeout(autoTimerRef.current); autoTimerRef.current = null; }
    setDeviationOn(false);
    setStage("TRIP_COMPLETED");
    setEndStep(incident && sosSheet !== "closed" ? "pay" : "pay");
  };

  const handleFeedbackDone = (record: AIFeedbackRecord, submitted: boolean) => {
    setFeedbackLog((prev) => {
      const log = [...prev, record];
      saveJSON("abhi_feedback_log", log);
      return log;
    });
    if (incident) {
      setEndStep("debrief");
    } else {
      finishRide(!submitted);
    }
  };

  const finishRide = (skipped: boolean) => {
    // Full state hygiene: nothing leaks into the next ride.
    setStage("SELECTING_DESTINATION");
    setDropoff(null); setRoutes([]); setSelectedRouteId(null); setDrivers([]);
    setSelectedDriver(null); setTripProgress(0);
    setThreatLevel("NORMAL"); setDistressScore(0);
    setIncident(null); setDispatchResult(null); setSosSheet("closed");
    autoSosArmedRef.current = false; setLivePos(null); setGpsLabel("acquiring GPS…");
    setEndStep("pay");
    if (skipped) {
      // Skipped once - the next ride will ask harder. (No punitive UI today.)
      console.info("Feedback skipped; will re-prompt next ride.");
    }
  };

  const resetAll = () => {
    audio.stopMonitoring();
    finishRide(false);
    setOnboarded(false);
  };

  // ── Render: one screen per stage ─────────────────────────────────
  return (
    <div className="app-frame">
      <TopBar
        riderName={riderName}
        threat={threatLevel}
        monitoring={audio.isMonitoring}
        onContacts={() => setIsContactsOpen(true)}
        onReset={onboarded ? resetAll : undefined}
      />
      <div className="app-scroll">
        {!onboarded ? (
          <Onboard
            draft={riderDraft}
            setDraft={setRiderDraft}
            contacts={contacts}
            onDone={() => {
              setRiderName(riderDraft.trim());
              saveJSON("abhi_rider", { name: riderDraft.trim() });
              setOnboarded(true);
            }}
            addContact={(c) => setContacts((prev) => { const n = [...prev, c]; saveJSON("abhi_emergency_contacts", n); return n; })}
            removeContact={(id) => setContacts((prev) => { const n = prev.filter((x) => x.id !== id); saveJSON("abhi_emergency_contacts", n); return n; })}
          />
        ) : (
          <>
            {stage === "SELECTING_DESTINATION" && (
              <Destination
                riderName={riderName}
                pickup={pickup}
                dropoff={dropoff}
                setPickup={setPickup}
                setDropoff={setDropoff}
                onGo={() => {
                  if (!dropoff) return;
                  setStage("ROUTE_SELECTION");
                  fetchRoutes();
                }}
              />
            )}
            {stage === "ROUTE_SELECTION" && (
              <RouteChoice
                pickup={pickup}
                dropoff={dropoff}
                routes={routes}
                loading={routesLoading}
                error={routesError}
                selectedId={selectedRouteId}
                onSelect={setSelectedRouteId}
                onRetry={fetchRoutes}
                onBack={() => setStage("SELECTING_DESTINATION")}
                onConfirm={() => setStage("SEARCHING_DRIVER")}
              />
            )}
            {stage === "SEARCHING_DRIVER" && (
              <div className="card center-screen" style={{ marginTop: 40 }}>
                <div className="spin" style={{ margin: "18px auto" }} />
                <p className="sheet-title">Finding you a driver…</p>
                <p className="sub">Sharing your safe route with verified Abhi AI drivers nearby.</p>
              </div>
            )}
            {stage === "CHOOSING_DRIVER" && (
              <DriverChoice
                drivers={drivers}
                onPick={(d) => { setSelectedDriver(d); setStage("DRIVER_ASSIGNED"); }}
                onBack={() => setStage("ROUTE_SELECTION")}
              />
            )}
            {stage === "DRIVER_ASSIGNED" && selectedDriver && (
              <Arrival
                driver={selectedDriver}
                route={activeRoute}
                pickup={pickup}
                dropoff={dropoff}
                onBoard={() => setPermOpen(true)}
                onBack={() => setStage("CHOOSING_DRIVER")}
              />
            )}
            {stage === "IN_TRIP" && (
              <Trip
                driver={selectedDriver}
                route={activeRoute}
                pickup={pickup}
                dropoff={dropoff}
                progress={tripProgress}
                tripMinutes={tripMinutes}
                audio={audio}
                threatLevel={threatLevel}
                distressScore={distressScore}
                gpsLabel={gpsLabel}
                currentPos={currentPos}
                deviationOn={deviationOn}
                dispatchMode={dispatchMode}
                onOpenDashboard={() => setIsDashOpen(true)}
                onSOS={manualSOS}
                onSimulate={simulateDanger}
                onArrive={arriveRide}
              />
            )}
            {stage === "TRIP_COMPLETED" && (
              <div className="card center-screen" style={{ marginTop: 30 }}>
                <div className="big-emoji">🏁</div>
                <p className="sheet-title">You've arrived</p>
                <p className="sub">Wrapping up your ride…</p>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Sheets ── */}
      <ContactsSheet
        open={isContactsOpen}
        contacts={contacts}
        onClose={() => setIsContactsOpen(false)}
        onSave={(n) => { setContacts(n); saveJSON("abhi_emergency_contacts", n); }}
      />
      <SosPromptSheet
        open={sosSheet === "prompt"}
        reason={sosReason}
        countdown={sosCountdown}
        onSafe={handleImSafe}
        onNow={() => { stopCountdown(); fireSOS(); }}
      />
      <SosResultsSheet
        open={sosSheet === "results"}
        result={dispatchResult}
        contacts={contacts}
        onSafe={() => { setSosSheet("closed"); setThreatLevel("ELEVATED"); }}
      />
      <PermissionSheet
        open={permOpen}
        onAllow={() => { setPermOpen(false); setStage("IN_TRIP"); audio.startMonitoring(); }}
        onSkip={() => { setPermOpen(false); setStage("IN_TRIP"); }}
      />
      <DashboardSheet open={isDashOpen} onClose={() => setIsDashOpen(false)} />
      <PaySheet
        open={stage === "TRIP_COMPLETED" && endStep === "pay"}
        distanceKm={activeRoute?.distanceKm || 0}
        farePkr={selectedDriver?.fareOfferPkr || 0}
        onDone={(m: PaymentMethod, t: number) => { setPayChoice({ method: m, total: t }); setEndStep("feedback"); }}
      />
      <FeedbackSheet
        open={stage === "TRIP_COMPLETED" && endStep === "feedback"}
        totalPkr={payChoice?.total ?? 0}
        onSubmit={handleFeedbackDone}
      />
      <DebriefSheet
        open={stage === "TRIP_COMPLETED" && endStep === "debrief"}
        incident={incident}
        dispatchResult={dispatchResult}
        onClose={() => finishRide(false)}
      />
    </div>
  );
}

/* ══════════════════════════ Screens ══════════════════════════ */

function TopBar({ threat, monitoring, onContacts, onReset }: any) {
  const chip =
    threat === "CRITICAL_SOS" ? <span className="chip bad">Danger</span>
    : threat === "ELEVATED" ? <span className="chip warn">Elevated</span>
    : threat === "MONITORING" ? <span className="chip info">Watching</span>
    : monitoring ? <span className="chip ok">Safe</span>
    : null;
  return (
    <div className="topbar">
      <div className="brand">
        <img src="/logo.png" alt="Abhi AI" />
        {/* No greeting here: the rider's name already opens the screen below
            ("Where to, Ayesha?"), so this row only duplicated it. */}
        <div className="name">Abhi AI</div>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {chip}
        <button className="icon-btn" onClick={onContacts} aria-label="Emergency contacts">👤</button>
        {onReset && (
          <button className="icon-btn" onClick={onReset} aria-label="New ride">↺</button>
        )}
      </div>
    </div>
  );
}

function Onboard({ draft, setDraft, contacts, onDone, addContact, removeContact }: any) {
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newEmail, setNewEmail] = useState("");
  return (
    <>
      <div className="steps"><i className="done" /><i className="now" /><i /></div>
      <h1 className="h-hero">Welcome to Abhi AI</h1>
      <p className="sub">Ride-hailing with an audio safety shield that listens for danger - never records.</p>
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="field">
          <label>Your name</label>
          <input className="input" placeholder="e.g. Ayesha" value={draft} onChange={(e) => setDraft(e.target.value)} />
        </div>
        <p className="section-title">Emergency contacts</p>
        <p className="sub" style={{ marginTop: -6 }}>When an SOS fires, every contact with an email gets the live-location alert. Add at least one.</p>
        {contacts.map((c: EmergencyContact) => (
          <div className="row" key={c.id}>
            <div className="grow"><div className="t">{c.name}</div><div className="s">{c.phone}{c.email ? ' | ' + c.email : ''}</div></div>
            <button className="icon-btn" onClick={() => removeContact(c.id)}>✕</button>
          </div>
        ))}
        <div style={{ display: "flex", gap: 8 }}>
          <input className="input" placeholder="Name" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <input className="input" placeholder="+92 3xx xxxxxxx" value={newPhone} onChange={(e) => setNewPhone(e.target.value)} />
        </div>
        <input className="input" placeholder="email (for SOS alerts)" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} style={{ marginTop: 6 }} />
        <button
          className="btn ghost"
          style={{ minHeight: 44 }}
          disabled={!newName.trim() || newPhone.trim().length < 8}
          onClick={() => {
            addContact({ id: `ec_${Date.now()}`, name: newName.trim(), relationship: "Contact", phone: newPhone.trim(), email: newEmail.trim() || undefined, isPrimary: contacts.length === 0, autoCallOnSos: true, autoSmsGpsOnSos: true });
            setNewName(""); setNewPhone(""); setNewEmail("");
          }}
        >
          + Add contact
        </button>
      </div>
      <div className="cta">
        <button className="btn primary" disabled={!draft.trim() || contacts.length === 0} onClick={onDone}>
          {contacts.length === 0 ? "Add a contact to continue" : "Start riding"}
        </button>
      </div>
    </>
  );
}

function Destination({ riderName, pickup, dropoff, setPickup, setDropoff, onGo }: any) {
  const [search, setSearch] = useState("");
  const [editTarget, setEditTarget] = useState<"pickup" | "dropoff">("dropoff");
  const pickRef = useRef<HTMLDivElement | null>(null);
  // Tapping a pin row nudges the page down a little - just enough that the
  // row stays half-visible and the search field + option list come into view
  // beneath it. A full scrollIntoView would slam the card to the top and
  // hide the map the rider may still be looking at.
  const pickTarget = (t: "pickup" | "dropoff") => {
    setEditTarget(t);
    requestAnimationFrame(() => {
      const scroller = pickRef.current?.closest(".app-scroll") as HTMLElement | null;
      const card = pickRef.current;
      if (!scroller || !card) return;
      const top = card.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop;
      scroller.scrollTo({ top: Math.max(0, top - 96), behavior: "smooth" });
    });
  };
  const list = POPULAR_LOCATIONS.filter(
    (l) => !search || (l.title + l.address).toLowerCase().includes(search.toLowerCase())
  );
  // A tap edits whichever field is highlighted - the old mockup's pickup row
  // was a no-op, so riders could never fix their pickup. Choosing the same
  // place for both fields just swaps the pair, the way every ride app does.
  const applyPick = (l: LocationItem) => {
    if (editTarget === "pickup") {
      if (dropoff && dropoff.id === l.id) setDropoff(pickup);
      setPickup(l);
    } else if (pickup.id === l.id) {
      if (dropoff) { const other = dropoff; setDropoff(l); setPickup(other); }
    } else {
      setDropoff(l);
    }
  };
  return (
    <>
      <div className="steps"><i className="now" /><i /><i /><i /></div>
      <h1 className="h-hero">Where to, {riderName.split(" ")[0]}?</h1>
      <div className="card map-card">
        <LiveMap
          pickup={pickup}
          dropoff={dropoff}
          rideStatus="SELECTING_DESTINATION"
          threatLevel="NORMAL"
          tripProgress={0}
          isAudioMonitoring={false}
          routes={[]}
          selectedRouteId={null}
          deviationPosition={null}
        />
        <span className="cap">The map glides to whichever pin you move.</span>
      </div>
      <div className="card pick-card" ref={pickRef} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div className={"pick-row" + (editTarget === "pickup" ? " active" : "")} onClick={() => pickTarget("pickup")}>
          <span className="pick-dot green" />
          <div className="pick-body">
            <div className="s">Pickup</div>
            <div className="t">{pickup.title}</div>
          </div>
        </div>
        <div className={"pick-row" + (editTarget === "dropoff" ? " active" : "")} onClick={() => pickTarget("dropoff")}>
          <span className="pick-dot red" />
          <div className="pick-body">
            <div className="s">Destination</div>
            <div className="t">{dropoff?.title || "Choose below"}</div>
          </div>
        </div>
      </div>
      <div className="field">
        <input className="input" placeholder={editTarget === "pickup" ? "Search pickup in Islamabad" : "Search destination in Islamabad"} value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>
      <div className="card tight">
        {list.map((l) => (
          <div
            className="pick-row"
            key={l.id}
            onClick={() => applyPick(l)}
          >
            <span className="pick-dot" style={{ background: (editTarget === "pickup" ? pickup.id : dropoff?.id) === l.id ? "var(--brand)" : "var(--line)" }} />
            <div className="pick-body">
              <div className="t">{l.title}</div>
              <div className="s">{l.address}</div>
            </div>
          </div>
        ))}
        {list.length === 0 && <p className="sub" style={{ textAlign: "center" }}>No matches - try another name.</p>}
      </div>
      <div className="cta">
        <button className="btn primary" disabled={!dropoff} onClick={onGo}>
          Show safe routes
        </button>
      </div>
    </>
  );
}

function RouteChoice({ pickup, dropoff, routes, loading, error, selectedId, onSelect, onRetry, onBack, onConfirm }: any) {
  return (
    <>
      <div className="steps"><i className="done" /><i className="now" /><i /><i /></div>
      <h1 className="h-hero">Pick your route</h1>
      <div className="card map-card">
        <LiveMap
          pickup={pickup}
          dropoff={dropoff}
          rideStatus="ROUTE_SELECTION"
          threatLevel="NORMAL"
          tripProgress={0}
          isAudioMonitoring={false}
          routes={routes}
          selectedRouteId={selectedId}
          deviationPosition={null}
        />
        <span className="cap">Tap a route below to light it up on the map.</span>
      </div>
      {error && (
        <div className="banner warn">
          <span className="grow">Live routing is unreachable - showing a direct corridor instead. You can retry.</span>
          <button className="btn ghost" style={{ minHeight: 34, padding: "4px 10px", fontSize: 13 }} onClick={onRetry}>Retry</button>
        </div>
      )}
      {loading && (
        <div className="card center-screen"><div className="spin" style={{ margin: "16px auto" }} /><p className="sub">Loading routes from live map data…</p></div>
      )}
      {routes.map((r: RouteOption) => {
        // The server returns "unrated" until the safety evidence engine exists,
        // so the card says that in words instead of inventing a number.
        const chipCls = r.safetyLevel === "safe" ? "ok" : r.safetyLevel === "moderate" ? "warn" : r.safetyLevel === "unrated" ? "gray" : "bad";
        const chipTxt = r.safetyLevel === "safe" ? "Safe" : r.safetyLevel === "moderate" ? "Moderate" : r.safetyLevel === "unrated" ? "Safety: not rated yet" : "Less safe";
        return (
          <div key={r.id} className={"card route-card" + (selectedId === r.id ? " sel" : "")} onClick={() => onSelect(r.id)}>
            <div className="route-head">
              <div><div className="t" style={{ fontWeight: 800 }}><span style={{ color: r.color || "var(--brand)" }}>●</span> {r.summary}</div></div>
              <span className={"chip " + chipCls}>{chipTxt}{r.safetyScore != null ? ` · ${r.safetyScore}` : ""}</span>
            </div>
            <div className="route-stats">
              <span>{r.distanceKm} km</span>
              <span>~{r.durationMin} min</span>
            </div>
          </div>
        );
      })}
      <div className="cta">
        <div className="btn-row">
          <button className="btn ghost" onClick={onBack}>Back</button>
          <button className="btn primary" disabled={!selectedId || loading} onClick={onConfirm}>
            Confirm route
          </button>
        </div>
      </div>
    </>
  );
}

// Card structure and wording are the desktop Abhi AI "Nearby Drivers" list
// (rider's call, 2026-10-22): name + star on one line, "car · plate" beneath,
// Rs. fare and ETA on the right, Accept as the action. Only the palette is new
// - the light theme. carModel already carries its trim colour in the data, so
// carColor is no longer prefixed on to it, and the Khwateen fleet reads as a
// badge instead of being fused into the driver's name.
function DriverChoice({ drivers, onPick, onBack }: any) {
  const [filter, setFilter] = useState<"all" | "female">("all");
  const shown = filter === "female" ? drivers.filter((d: DriverProfile) => d.isFemaleDriver) : drivers;
  return (
    <>
      <div className="steps"><i className="done" /><i className="done" /><i className="now" /><i /></div>
      <div className="drv-head">
        <div className="drv-head-l">
          <Radar className="drv-radar" />
          <h1 className="h-hero">Nearby Drivers</h1>
        </div>
        <span className="drv-count">{shown.length} available</span>
      </div>
      <div className="seg-row">
        <button className={"seg" + (filter === "all" ? " on" : "")} onClick={() => setFilter("all")}>All ({drivers.length})</button>
        <button className={"seg fem" + (filter === "female" ? " on" : "")} onClick={() => setFilter("female")}>Khwateen</button>
      </div>
      <div className="drv-list">
        {shown.map((d: DriverProfile) => (
          <div className={"drv-row" + (d.isFemaleDriver ? " fem" : "")} key={d.id}>
            <div className={"drv-tile " + (d.isFemaleDriver ? "fem" : "mal")} title={d.carModel}>
              <Car />
            </div>
            <div className="drv-id">
              <div className="drv-name">
                <span className="drv-nm">{d.name}</span>
                <span className="drv-star">★ {d.rating}</span>
                {d.isFemaleDriver && <span className="drv-badge">Khwateen</span>}
              </div>
              <p className="drv-car">{d.carModel} · <span className="drv-plate">{d.licensePlate}</span></p>
            </div>
            <div className="drv-fare">
              <div className="drv-rs">Rs. {d.fareOfferPkr}</div>
              <div className="drv-eta">{d.etaMinutes} min</div>
            </div>
            <button className="drv-accept" onClick={() => onPick(d)}>Accept</button>
          </div>
        ))}
        {shown.length === 0 && (
          <div className="card center-screen"><p className="sub">No drivers in this fleet right now - try All drivers.</p></div>
        )}
      </div>
      <div className="cta">
        <button className="btn ghost" onClick={onBack}>Change route</button>
      </div>
    </>
  );
}

function Arrival({ driver, route, pickup, dropoff, onBoard, onBack }: any) {
  const otp = String(1000 + (driver.id.charCodeAt(driver.id.length - 1) * 37) % 9000);
  return (
    <>
      <div className="steps"><i className="done" /><i className="done" /><i className="done" /><i className="now" /></div>
      <h1 className="h-hero">Your driver is on the way</h1>
      <div className="card">
        <div className="driver-head">
          <div className={"car-tile " + (driver.isFemaleDriver ? "fem" : "mal")} style={{ width: 54, height: 54 }} title={`${driver.carColor} ${driver.carModel}`}>
            <Car style={{ width: 26, height: 26 }} />
          </div>
          <div className="driver-meta" style={{ flex: 1 }}>
            <div className="t">{driver.name}</div>
            <div className="s">{driver.carColor} {driver.carModel} · arriving in {driver.etaMinutes} min</div>
            <div className="s" style={{ marginTop: 4 }}>Plate: <span className="plate">{driver.licensePlate}</span></div>
          </div>
        </div>
        <div className="otp" style={{ marginTop: 14 }}>{otp}</div>
        <p className="sub" style={{ textAlign: "center", marginTop: 8 }}>
          Share this code only with a driver whose plate matches. Board when it does.
        </p>
      </div>
      <div className="card map-card">
        <LiveMap
          pickup={pickup}
          dropoff={dropoff}
          rideStatus="DRIVER_ASSIGNED"
          threatLevel="NORMAL"
          tripProgress={0}
          selectedDriver={driver}
          isAudioMonitoring={false}
          routes={route ? [route] : []}
          selectedRouteId={route?.id ?? null}
          deviationPosition={null}
        />
        <span className="cap">The car moves along the route toward your pickup.</span>
      </div>
      <div className="banner info"><span className="grow">Abhi AI monitoring starts the moment you board: dial, route check, one-touch SOS.</span></div>
      <div className="cta">
        <div className="btn-row">
          <button className="btn ghost" onClick={onBack}>Cancel</button>
          <button className="btn primary" onClick={onBoard}>Code matches - board</button>
        </div>
      </div>
    </>
  );
}

function Trip({ driver, route, pickup, dropoff, progress, tripMinutes, audio, threatLevel, distressScore, gpsLabel, currentPos, deviationOn, dispatchMode, onOpenDashboard, onSOS, onSimulate, onArrive }: any) {
  const status =
    audio.monitorStatus === "disconnected" ? <><span className="dot red" /> Safety AI disconnected</>
    : audio.monitorStatus === "connecting" ? <><span className="dot amber" /> Connecting to Safety AI…</>
    : audio.isMonitoring ? <><span className="dot green" /> Safety AI live</>
    : <><span className="dot gray" /> Monitor off</>;
  const hot = threatLevel === "CRITICAL_SOS" || threatLevel === "ELEVATED";

  return (
    <>
      <div className="card tight">
        <div className="driver-head" style={{ alignItems: "center" }}>
          <div className={"car-tile " + (driver?.isFemaleDriver ? "fem" : "mal")} style={{ width: 40, height: 40, borderRadius: 12 }} title={`${driver?.carColor} ${driver?.carModel}`}>
            <Car style={{ width: 20, height: 20 }} />
          </div>
          <div className="driver-meta" style={{ flex: 1 }}>
            <div className="t">{driver?.name}</div>
            <div className="s"><span className="plate" style={{ fontSize: 11, padding: "1px 6px" }}>{driver?.licensePlate}</span></div>
          </div>
          <span className="chip info">{Math.max(0, Math.round(tripMinutes * (1 - progress)))} min left</span>
        </div>
      </div>

      <div className="card map-card">
        <LiveMap
          pickup={pickup}
          dropoff={dropoff}
          rideStatus="IN_TRIP"
          threatLevel={threatLevel}
          tripProgress={Math.round(progress * 100)}
          selectedDriver={driver ?? undefined}
          isAudioMonitoring={audio.isMonitoring}
          routes={route ? [route] : []}
          selectedRouteId={route?.id ?? null}
          deviationPosition={null}
        />
        <span className="cap">{gpsLabel}</span>
      </div>

      {deviationOn && (
        <div className="banner bad"><span className="grow">Off the agreed route. Ask the driver why - or take action below.</span></div>
      )}
      {audio.monitorStatus === "disconnected" && (
        <div className="banner bad"><span className="grow">Audio brain unreachable - dial is frozen. Route checks + SOS still work. Restart monitor or ride on with manual watch.</span></div>
      )}
      {dispatchMode === "mock" && (
        <div className="banner info"><span className="grow">SOS email isn't configured on this machine (Brevo keys missing in .env). The alert is still captured with your live location.</span></div>
      )}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span className="chip gray">{status}</span>
          <span className={"chip " + (threatLevel === "CRITICAL_SOS" ? "bad" : threatLevel === "ELEVATED" ? "warn" : threatLevel === "MONITORING" ? "info" : "ok")}>
            {threatLevel === "CRITICAL_SOS" ? "Danger" : threatLevel === "ELEVATED" ? "Elevated" : threatLevel === "MONITORING" ? "Watching" : "Calm"}
          </span>
        </div>
        {/* Dial left, real actions right: the empty band beside the dial used
            to be dead space - the rider's fix, 2026-10-22. Evidence spans full
            width below so the transcript is never squeezed into half a column. */}
        <div className="trip-grid">
          <div className="trip-dial">
            <DangerGauge score={distressScore} label={audio.dialLabel} onClick={onOpenDashboard} />
            <Wave levels={audio.getAudioLevels()} hot={hot} />
          </div>
          <div className="trip-actions">
            {/* Only genuine in-ride actions live here. The dashboard opens by
                tapping the dial (v1 pattern); "call driver" was dropped - you
                are already in the car with them. */}
            <button className="btn ghost" onClick={() => {
              const link = mapsLinkFor(currentPos ?? { lat: pickup.lat, lng: pickup.lng });
              if (navigator.share) navigator.share({ title: "My location - Abhi AI", url: link }).catch(() => {});
              else navigator.clipboard?.writeText(link);
            }}>Share my location</button>
            <button className="btn primary" onClick={onArrive}>Arrived</button>
          </div>
        </div>
        <details className="ai-evidence">
          <summary>What Abhi AI is hearing</summary>
          <div className="transcript">
            {audio.transcript
              ? `“…${String(audio.transcript).slice(-140)}”`
              : audio.isMonitoring
                ? "Nothing picked up yet - quiet cabin."
                : "Monitor off. The mic was not allowed, so nothing is being analyzed."}
          </div>
          {audio.lastResult && (
            <div className="heard">
              Heard: {audio.lastResult.sound_name} ({audio.lastResult.confidence > 1 ? Math.round(audio.lastResult.confidence) : Math.round(audio.lastResult.confidence * 100)}%
              {audio.lastResult.custom_label ? ` · AI class: ${audio.lastResult.custom_label}` : ""})
            </div>
          )}
          {audio.lastResult?.keywords?.length > 0 && (
            <div className="kw-row">{audio.lastResult.keywords.map((k: string, i: number) => <span key={i} className="kw">{k}</span>)}</div>
          )}
        </details>
      </div>

      <div className="sos-row">
        {/* Demo control tucked to the side of the siren, small and clearly a
            rehearsal aid - not one of the rider's real actions. */}
        <button className="demo-side" onClick={onSimulate} title="Demo only: fake a distress spike">Demo ⚡</button>
        <SosHoldButton onConfirm={onSOS} />
        <span className="sos-side-spacer" aria-hidden />
      </div>
    </>
  );
}

/** Hold-to-confirm SOS: a round siren-style button that fills its ring over
    0.9s. Deliberate enough to avoid pocket-fire, one-thumb reachable, and far
    less clunky than the old full-width "HOLD FOR SOS" bar. */
function SosHoldButton({ onConfirm }: { onConfirm: () => void }) {
  const [hold, setHold] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const NEED = 900;
  const start = () => {
    let n = 0;
    timerRef.current = setInterval(() => {
      n += 30;
      setHold(n);
      if (n >= NEED) {
        if (timerRef.current) clearInterval(timerRef.current);
        setHold(0);
        onConfirm();
      }
    }, 30);
  };
  const cancel = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setHold(0);
  };
  const pct = Math.min(100, (hold / NEED) * 100);
  return (
    <button
      className="sos-hold"
      onPointerDown={start}
      onPointerUp={cancel}
      onPointerLeave={cancel}
      onPointerCancel={cancel}
      style={{ ["--fill" as any]: `${pct}%` }}
      aria-label="Hold for SOS"
    >
      <span className="sos-hold-core">
        <span className="sos-hold-txt">SOS</span>
      </span>
      <span className="sos-hold-hint">hold</span>
    </button>
  );
}

function SosPromptSheet({ open, reason, countdown, onSafe, onNow }: any) {
  return (
    <BottomSheet open={open}>
      {/* No backdrop dismiss, no pause: the countdown is the verification. */}
      <p className="sheet-title">Are you okay?</p>
      <p className="sub">{reason}</p>
      <div className="count-ring">{countdown}</div>
      <p className="sub" style={{ textAlign: "center" }}>
        In {countdown}s we send your live location to your emergency contacts. This timer cannot be paused.
      </p>
      <button className="btn primary" onClick={onSafe}>I am safe</button>
      <button className="btn danger" onClick={onNow}>Send SOS now</button>
    </BottomSheet>
  );
}

function SosResultsSheet({ open, result, contacts, onSafe }: any) {
  return (
    <BottomSheet open={open}>
      <p className="sheet-title">SOS sent</p>
      {result?.mapsLink && (
        <div className="banner info"><span className="grow">Live location: </span><a href={result.mapsLink} target="_blank" rel="noreferrer" style={{ fontWeight: 800 }}>open map</a></div>
      )}
      {(result?.results || []).map((r: any, i: number) => (
        <div key={i} className={"banner " + (r.ok ? "ok" : "bad")}>
          <span className="grow">{r.ok ? "Email alert: " : "Email not sent: "}{r.detail}</span>
        </div>
      ))}
      {!result?.success && result?.error && (
        <div className="banner bad"><span className="grow">Dispatch server unreachable - dial manually below.</span></div>
      )}
      {contacts.filter((c: EmergencyContact) => c.autoCallOnSos).map((c: EmergencyContact) => (
        <a key={c.id} className="btn" href={`tel:${c.phone.replace(/\s/g, "")}`}>Call {c.name}</a>
      ))}
      <div className="btn-row">
        <a className="btn danger" href="tel:15">Police 15</a>
        <a className="btn" href="tel:1122">Rescue 1122</a>
      </div>
      <button className="btn ghost" onClick={onSafe}>I'm safe now - stand down</button>
    </BottomSheet>
  );
}

function ContactsSheet({ open, contacts, onClose, onSave }: any) {
  const [draftName, setDraftName] = useState("");
  const [draftPhone, setDraftPhone] = useState("");
  const [draftEmail, setDraftEmail] = useState("");
  const [list, setList] = useState<EmergencyContact[]>(contacts);
  useEffect(() => { if (open) setList(contacts); }, [open, contacts]);

  const persist = (n: EmergencyContact[]) => { setList(n); onSave(n); };

  return (
    <BottomSheet open={open} onClose={onClose}>
      <p className="sheet-title">Emergency contacts</p>
      {list.map((c) => (
        <div className="row" key={c.id}>
          <div className="grow"><div className="t">{c.name}</div><div className="s">{c.phone}{c.email ? ' | ' + c.email : ''}</div></div>
          <button
            className={"chip " + (c.autoSmsGpsOnSos ? "ok" : "gray")}
            onClick={() => persist(list.map((x) => (x.id === c.id ? { ...x, autoSmsGpsOnSos: !x.autoSmsGpsOnSos, autoCallOnSos: !x.autoSmsGpsOnSos } : x)))}
          >
            {c.autoSmsGpsOnSos ? "auto-notify on" : "auto-notify off"}
          </button>
          <button className="icon-btn" onClick={() => persist(list.filter((x) => x.id !== c.id))}>✕</button>
        </div>
      ))}
      <div style={{ display: "flex", gap: 8 }}>
        <input className="input" placeholder="Name" value={draftName} onChange={(e) => setDraftName(e.target.value)} />
        <input className="input" placeholder="+92…" value={draftPhone} onChange={(e) => setDraftPhone(e.target.value)} />
      </div>
      <input className="input" placeholder="email (for SOS alerts)" value={draftEmail} onChange={(e) => setDraftEmail(e.target.value)} style={{ marginTop: 6 }} />
      <button
        className="btn ghost"
        style={{ minHeight: 44 }}
        disabled={!draftName.trim() || draftPhone.trim().length < 8}
        onClick={() => {
          persist([...list, { id: `ec_${Date.now()}`, name: draftName.trim(), relationship: "Contact", phone: draftPhone.trim(), email: draftEmail.trim() || undefined, isPrimary: false, autoCallOnSos: true, autoSmsGpsOnSos: true }]);
          setDraftName(""); setDraftPhone(""); setDraftEmail("");
        }}
      >
        + Add
      </button>
      <button className="btn primary" onClick={onClose}>Done</button>
    </BottomSheet>
  );
}

// Permission priming (ported from the desktop app's privacy explainer): the
// rider is told what the mic does - and does not do - BEFORE the browser
// prompt lands, which is when trust is actually won or lost.
function PermissionSheet({ open, onAllow, onSkip }: any) {
  return (
    <BottomSheet open={open}>
      <p className="sheet-title">Turn on your safety shield</p>
      <p className="sub">
        From the moment you board, Abhi AI listens for danger sounds and words of
        distress - screams, “bachao”, “gaadi roko”. It reacts in the cabin and it
        never records or uploads your conversation. Your browser will now ask for
        mic access: choose Allow.
      </p>
      <button className="btn primary" onClick={onAllow}>Allow mic - start watching</button>
      <button className="btn ghost" onClick={onSkip}>Ride without monitoring</button>
    </BottomSheet>
  );
}

// The brain's own dashboard, embedded as a sheet so the rider can verify the
// AI live instead of taking the dial on faith. Host follows the page, so a
// phone on the same Wi-Fi opens the board from the machine running the brain.
function DashboardSheet({ open, onClose }: any) {
  return (
    <BottomSheet open={open} onClose={onClose}>
      <p className="sheet-title">Live AI dashboard</p>
      <p className="sub">The audio brain's own board: dial, per-chunk analysis, journey log.</p>
      <iframe className="dash-frame" src={`http://${BRAIN_HOST}:5004`} title="Abhi AI dashboard" />
      <button className="btn ghost" onClick={onClose}>Close</button>
    </BottomSheet>
  );
}
