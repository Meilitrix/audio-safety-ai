import React, { useEffect, useState } from "react";

/** Mobile bottom sheet with backdrop dismiss. */
export function BottomSheet({
  open,
  onClose,
  children,
  dark,
}: {
  open: boolean;
  onClose?: () => void;
  children: React.ReactNode;
  dark?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="sheet-root">
      <div className="sheet-backdrop" onClick={onClose} />
      <div className={"sheet" + (dark ? " dark" : "")} role="dialog" aria-modal="true">
        <div className="sheet-grab" />
        {children}
      </div>
    </div>
  );
}

/** Live loudness bars, driven by the mic levels the hook already computes. */
export function Wave({ levels, hot }: { levels: number[]; hot: boolean }) {
  const [, force] = useState(0);
  useEffect(() => {
    const id = setInterval(() => force((n) => n + 1), 120);
    return () => clearInterval(id);
  }, []);
  return (
    <div className={"wave" + (hot ? " hot" : "")}>
      {levels.map((v, i) => (
        <i key={i} style={{ height: `${Math.max(3, v * 100)}%` }} />
      ))}
    </div>
  );
}
