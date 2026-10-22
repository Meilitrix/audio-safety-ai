import React, { useState } from "react";
import { BottomSheet } from "./Sheet";
import { PaymentMethod, AIFeedbackRecord, IncidentReport } from "../types";

// Pakistan's real rails (rider's call, 2026-10-22): cash dominates, wallets
// (JazzCash/EasyPaisa) are the digital default and pay by scanning the
// driver's raast/EasyPaisa QR in the car, card is rare. "Abhi Pay" was dropped
// on purpose - we are the safety layer, not a wallet asking to hold money.
const PAY_OPTIONS: { id: PaymentMethod; label: string; note: string; detail: string }[] = [
  { id: "cash", label: "Cash", note: "Pay the driver at drop-off", detail: "Hand the driver the exact fare when you reach your stop. No card, no app - still the most common way people pay in Islamabad." },
  { id: "jazzcash", label: "JazzCash", note: "Scan the driver's JazzCash QR in the car", detail: "Open JazzCash and scan the driver's QR in the car. The money goes straight to their wallet - Abhi AI never holds or routes your payment." },
  { id: "easypaisa", label: "EasyPaisa", note: "Scan the driver's EasyPaisa QR in the car", detail: "Open EasyPaisa and scan the driver's QR in the car. Sent person-to-person; we don't touch the money." },
  { id: "credit_card", label: "Card", note: "Visa / Mastercard", detail: "Visa / Mastercard / PayPak, charged automatically when the trip ends." },
];

/** Step 1 of ride end. The fare is the price the rider already agreed with the
 *  driver (the fixed inDrive-style offer shown on their card) - we do NOT invent
 *  a base+distance+time formula that diverges from what was accepted at booking.
 *  And safety is never a line item: Abhi AI is the free safety layer, so charging
 *  for it at the end would contradict the whole pitch. */
export function PaySheet({
  open,
  farePkr,
  distanceKm,
  onDone,
}: {
  open: boolean;
  farePkr: number;
  distanceKm: number;
  onDone: (method: PaymentMethod, total: number) => void;
}) {
  const [method, setMethod] = useState<PaymentMethod>("cash");

  return (
    <BottomSheet open={open}>
      <p className="sheet-title">Fare</p>
      <div className="card tight">
        <div className="row">
          <div className="grow">
            <div className="t">Trip fare</div>
            <div className="s">
              Agreed with your driver{distanceKm ? ` · ${distanceKm} km` : ""}
            </div>
          </div>
          <div className="t">Rs {farePkr}</div>
        </div>
        <div className="row">
          <div className="grow">
            <div className="s">Safety AI monitoring</div>
          </div>
          <div className="t" style={{ color: "var(--teal)" }}>Free</div>
        </div>
        <div className="row">
          <div className="grow">
            <div className="t">Total</div>
          </div>
          <div className="t" style={{ color: "var(--brand)" }}>Rs {farePkr}</div>
        </div>
      </div>
      <div className="opt-row">
        {PAY_OPTIONS.map((p) => (
          <button key={p.id} className={"opt" + (method === p.id ? " on" : "")} onClick={() => setMethod(p.id)}>
            {p.label}
          </button>
        ))}
      </div>
      {/* The selected chip reveals its own content, so tapping a method actually
          explains how that method works instead of a one-line hint. */}
      <div className="pay-detail">
        <div className="pay-detail-title">{PAY_OPTIONS.find((p) => p.id === method)?.label}</div>
        <div className="pay-detail-body">{PAY_OPTIONS.find((p) => p.id === method)?.detail}</div>
      </div>
      <button className="btn primary" onClick={() => onDone(method, farePkr)}>
        Confirm & rate ride
      </button>
    </BottomSheet>
  );
}

/** Step 2: feedback is REQUIRED to close the ride (records persist + POST). */
export function FeedbackSheet({
  open,
  totalPkr,
  onSubmit,
}: {
  open: boolean;
  totalPkr: number;
  onSubmit: (record: AIFeedbackRecord, submitted: boolean) => void;
}) {
  const [rating, setRating] = useState(0);
  const [falseAlarms, setFalseAlarms] = useState<AIFeedbackRecord["falseAlarms"] | null>(null);
  const [dialClarity, setDialClarity] = useState<AIFeedbackRecord["dialClarity"] | null>(null);
  const [busy, setBusy] = useState(false);

  const complete = rating > 0 && falseAlarms !== null && dialClarity !== null;

  const send = async (submitted: boolean) => {
    const record: AIFeedbackRecord = {
      id: `fb_${Date.now()}`,
      timestamp: new Date().toISOString(),
      rating: rating || 3,
      falseAlarms: falseAlarms || "none",
      dialClarity: dialClarity || "clear",
      comments: "",
    };
    if (submitted) {
      setBusy(true);
      try {
        await fetch("/api/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...record, totalPkr }),
        });
      } catch {
        /* offline still counts as answered locally */
      }
      setBusy(false);
    }
    onSubmit(record, submitted);
  };

  return (
    <BottomSheet open={open}>
      <p className="sheet-title">How was the ride?</p>
      <div className="stars">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} className={n <= rating ? "on" : ""} onClick={() => setRating(n)} aria-label={`${n} stars`}>
            ★
          </button>
        ))}
      </div>
      <p className="section-title">Did Abhi AI alarm when nothing was wrong?</p>
      <div className="opt-row">
        {(["none", "once", "repeatedly"] as const).map((v) => (
          <button key={v} className={"opt" + (falseAlarms === v ? " on" : "")} onClick={() => setFalseAlarms(v)}>
            {v === "none" ? "No, it stayed quiet" : v === "once" ? "Once" : "Repeatedly"}
          </button>
        ))}
      </div>
      <p className="section-title">Was the risk dial easy to understand?</p>
      <div className="opt-row">
        {(["clear", "somewhat", "confusing"] as const).map((v) => (
          <button key={v} className={"opt" + (dialClarity === v ? " on" : "")} onClick={() => setDialClarity(v)}>
            {v === "clear" ? "Very clear" : v === "somewhat" ? "Sort of" : "Confusing"}
          </button>
        ))}
      </div>
      <button className="btn primary" disabled={!complete || busy} onClick={() => send(true)}>
        {busy ? "Sending…" : "Submit feedback"}
      </button>
      <button className="btn ghost" onClick={() => send(false)} style={{ minHeight: 40, fontSize: 13.5 }}>
        Skip this time
      </button>
    </BottomSheet>
  );
}

/** Only appears if an SOS actually fired this ride: what really happened. */
export function DebriefSheet({
  open,
  incident,
  dispatchResult,
  onClose,
}: {
  open: boolean;
  incident: IncidentReport | null;
  dispatchResult: any;
  onClose: () => void;
}) {
  return (
    <BottomSheet open={open} onClose={onClose}>
      <p className="sheet-title">Safety debrief</p>
      {incident ? (
        <>
          <div className="card tight">
            <div className="row">
              <div className="grow">
                <div className="t">{incident.incidentId}</div>
                <div className="s">{incident.summary}</div>
              </div>
              <span className="chip bad">{incident.severity}</span>
            </div>
          </div>
          {dispatchResult?.mapsLink && (
            <a className="btn" href={dispatchResult.mapsLink} target="_blank" rel="noreferrer">
              Open live location
            </a>
          )}
          {(dispatchResult?.results || []).map((r: any, i: number) => (
            <div className={"banner " + (r.ok ? "ok" : "bad")} key={i}>
              <span className="grow">{r.ok ? "Email alert: " : "Email not sent: "}{r.detail}</span>
            </div>
          ))}
        </>
      ) : (
        <p className="sub">No SOS was triggered on this ride. Your safety log stayed clean.</p>
      )}
      <button className="btn primary" onClick={onClose}>Done</button>
    </BottomSheet>
  );
}
