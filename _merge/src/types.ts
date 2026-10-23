export type RideStatus =
  | "WELCOME_LANDING"
  | "SELECTING_DESTINATION"
  | "ROUTE_SELECTION"
  | "SEARCHING_DRIVER"
  | "CHOOSING_DRIVER"
  | "DRIVER_ASSIGNED"
  | "IN_TRIP"
  | "TRIP_COMPLETED";

export type ThreatLevel = "NORMAL" | "MONITORING" | "ELEVATED" | "CRITICAL_SOS";

export interface LocationItem {
  id: string;
  title: string;
  subtitle: string;
  address: string;
  lat: number;
  lng: number;
  city: "Lahore" | "Karachi" | "Islamabad";
  category: "airport" | "transit" | "business" | "entertainment" | "popular";
}

export interface RideOption {
  id: string;
  name: string;
  tier: string;
  description: string;
  capacity: number;
  etaMin: number;
  basePrice: number; // in PKR (Rs.)
  price: number; // in PKR (Rs.)
  safetyTier: string;
  carType: string;
  iconType: "compact" | "comfort" | "shield" | "xl" | "female";
  isFemaleOnlyFleet?: boolean;
}

export interface DriverProfile {
  id: string;
  name: string;
  gender: "female" | "male";
  isFemaleDriver: boolean;
  rating: number;
  totalTrips: number;
  carModel: string;
  carColor: string;
  licensePlate: string;
  photoUrl: string;
  // Optional: a photo of the driver's CAR (used instead of a face for the
  // Khawateen driver who prefers her vehicle shown rather than her picture).
  carPhotoUrl?: string;
  phone: string;
  audioSafetyCertified: boolean;
  activeBadge: string;
  fareOfferPkr: number; // inDrive-style bid in PKR
  distanceKm: number;
  etaMinutes: number;
}

export interface AcousticEvent {
  id: string;
  timestamp: string;
  type?: "ENGINE_AMBIENT" | "TRAFFIC_HONK" | "RICKSHAW_MOTOR" | "VOICE_SPEECH" | "SHOUTING" | "DISTRESS_CRY";
  category?: string;
  decibels: number;
  isRegularJourneyNoise?: boolean;
  isFilteredAsSafe?: boolean;
  label: string;
  description: string;
}

export interface SpeechTranscriptEntry {
  id: string;
  timestamp: string;
  speaker: "Rider (Aap)" | "Driver" | "Unknown Ambient";
  text: string;
  tone: "Calm" | "Neutral" | "Irritated" | "Agitated" | "Hostile" | "Screaming" | "Pleading" | "Screaming/Pleading" | "Pleading/Emergency";
  distressFlag: boolean;
  detectedKeywords: string[];
}

export interface RiskPattern {
  id: string;
  timestamp: number; // ms
  timeString?: string;
  type: "ELEVATED_ARGUMENT" | "THREATENING_TONE" | "DISTRESS_KEYWORD" | "ROUTE_DEVIATION_DISPUTE" | "DOOR_LOCK_PANIC" | string;
  severity?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
  description?: string;
  decibels?: number;
  triggerSnippet?: string;
}

export interface AudioSampleChunk {
  timestamp: number;
  decibels: number;
  threatLevel: ThreatLevel;
  distressScore: number;
  category: "REGULAR_ENGINE_TRAFFIC" | "TRAFFIC_HONKS" | "SUSPICIOUS_OUTBURSTS" | "DISTRESS_CRY";
  riderTone: string;
  driverTone: string;
  detectedKeywords: string[];
  snippet: string;
  escalationDetected: boolean;
}

export interface IncidentReport {
  incidentId: string;
  timestamp: string;
  isoTime: string;
  severity: ThreatLevel;
  category: "NONE" | "VERBAL_ABUSE" | "HARASSMENT" | "VIOLENT_ACTIVITY" | "DIRECT_DISTRESS_KEYWORD" | "VOICE_DISTRESS_SCREAM";
  summary: string;
  detectedKeywords: string[];
  transcriptSnippet: string;
  riderTone: string;
  driverTone: string;
  backgroundAcoustic: string;
  distressScore: number;
  gpsCoordinates: {
    lat: number;
    lng: number;
    address: string;
    city?: string;
  };
  vehicleDetails: {
    driverName: string;
    vehicle: string;
    plate: string;
    riderName: string;
    driverPhone?: string;
  };
  emergencyDispatched: boolean;
  dispatchUnit?: string;
  dialedNumber?: string;
  actionsTaken: string[];
}

export type PaymentMethod = "jazzcash" | "easypaisa" | "credit_card" | "cash";

export interface EmergencyContact {
  id: string;
  name: string;
  relationship: string;
  phone: string;
  email?: string;
  isPrimary: boolean;
  autoCallOnSos: boolean;
  autoSmsGpsOnSos: boolean;
}

// Only questions a rider can actually perceive.  Model accuracy is measured in
// the labelling dashboard, not by asking passengers to grade detection.
export interface AIFeedbackRecord {
  id: string;
  timestamp: string;
  rating: number; // 1-5, the ride itself
  falseAlarms: "none" | "once" | "repeatedly";
  dialClarity: "clear" | "somewhat" | "confusing";
  comments: string;
}

// ── Route types ──────────────────────────────────────────────────────────────

export type RouteSafetyLevel = "safe" | "moderate" | "less_safe" | "unrated";

// Evidence behind a route's safety score - measured from open map data along
// the route corridor. null means "not mapped here", not "unsafe".
export interface RouteSafetyEvidence {
  score: number;
  level: RouteSafetyLevel;
  litSharePct: number | null; // % of checkpoints near a lit street
  helpMeters: number | null; // metres to nearest mapped police/hospital/clinic
  helpKind: string | null;
  activityPerKm: number | null; // mapped places per km (eyes on the street)
  checkpoints: number;
  reasons: string[]; // human-readable "why" bullets
}

export interface RouteOption {
  id: string;
  geometry: [number, number][]; // [lat, lng] pairs
  distanceKm: number;
  durationMin: number;
  safetyLevel: RouteSafetyLevel;
  safetyScore: number | null; // null until the evidence engine scores it
  summary: string; // e.g. "Via Canal Bank Road"
  color?: string; // optional display colour (used by the desktop LiveMap)
  evidenceStatus?: string; // "scored" | "unmapped_area" | "no_data"
  safety?: RouteSafetyEvidence; // present only when evidence was found
}

export interface DeviationAlert {
  isActive: boolean;
  deviationMeters: number;
  durationSeconds: number;
  acknowledged: boolean;
}
