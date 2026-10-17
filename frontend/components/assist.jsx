"use client";

import { useEffect, useState } from "react";

/** Live countdown to an ISO timestamp. */
export function Countdown({ until, onExpire }) {
  const [left, setLeft] = useState(() => Math.max(0, new Date(until).getTime() - Date.now()));
  useEffect(() => {
    const t = setInterval(() => {
      const ms = Math.max(0, new Date(until).getTime() - Date.now());
      setLeft(ms);
      if (ms === 0) {
        clearInterval(t);
        onExpire?.();
      }
    }, 500);
    return () => clearInterval(t);
  }, [until, onExpire]);
  const s = Math.ceil(left / 1000);
  const urgent = s <= 30;
  return (
    <span className={`font-mono text-sm font-semibold ${urgent ? "text-danger" : "text-slate"}`}>
      {Math.floor(s / 60)}:{String(s % 60).padStart(2, "0")} left
    </span>
  );
}

/** The big number the owner reads out to their helper. */
export function MatchCodeDisplay({ code }) {
  return (
    <div className="mx-auto flex h-40 w-56 items-center justify-center rounded-3xl bg-ink shadow-lg">
      <span className="font-mono text-7xl font-bold tracking-widest text-amber">{code}</span>
    </div>
  );
}

/** Three choices for the helper; only one matches what the owner sees. */
export function MatchCodePicker({ choices, value, onChange }) {
  return (
    <div
      className="grid grid-cols-3 gap-3"
      role="radiogroup"
      aria-label="Number shown on their screen"
    >
      {choices.map((c) => (
        <button
          key={c}
          type="button"
          role="radio"
          aria-checked={value === c}
          onClick={() => onChange(c)}
          className={`rounded-2xl border-2 py-6 font-mono text-4xl font-bold transition ${
            value === c
              ? "border-teal bg-teal-soft text-teal"
              : "border-line bg-white text-slate-900 hover:border-slate"
          }`}
        >
          {c}
        </button>
      ))}
    </div>
  );
}
