"use client";

import Link from "next/link";

// ---------------------------------------------------------------- icons (inline, no icon library)

export function ShieldIcon({ className = "h-5 w-5" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <path
        d="M12 2.8 5 5.6v5.6c0 4.5 3 8.4 7 9.9 4-1.5 7-5.4 7-9.9V5.6l-7-2.8Z"
        stroke="#3B82F6"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="m8.8 12.2 2.3 2.3 4.2-4.6"
        stroke="#60A5FA"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Brand lock-up: clean professional tile with shield + wordmark. */
export function Brand() {
  return (
    <Link href="/" className="inline-flex w-max items-center gap-3" aria-label="Kavach home">
      <span className="grid h-9 w-9 place-items-center rounded-xl border border-slate-700 bg-slate-800/90 shadow-sm">
        <ShieldIcon className="h-5 w-5" />
      </span>
      <div className="flex flex-col">
        <span className="font-display text-[19px] font-bold tracking-tight text-white">
          Kavach
        </span>
        <span className="text-[10px] font-medium text-slate-400">
          Passkey Identity
        </span>
      </div>
    </Link>
  );
}

export function ArrowDisc({ className = "" }) {
  return (
    <span
      className={`grid h-7 w-7 place-items-center rounded-lg bg-blue-600 text-sm leading-none text-white ${className}`}
      aria-hidden="true"
    >
      ↗
    </span>
  );
}

export function KeyIcon({ className = "h-4 w-4" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <circle cx="7.5" cy="15.5" r="4.5" />
      <path d="m10.7 12.3 9.3-9.3M17 6l3 3M14 9l2 2" strokeLinecap="round" />
    </svg>
  );
}

export function FingerprintIcon({ className = "h-5 w-5" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M6.5 6.5A7.5 7.5 0 0 1 19.5 12v1.5M4.5 10a7.5 7.5 0 0 0-.5 2.5c0 2 .4 3.6 1 5" />
      <path d="M8 12a4 4 0 0 1 8 0c0 3-.5 5.5-1.5 7.5M12 12c0 3.5-.7 6.5-2 8.5M8.2 15.5c-.2 1.5-.6 2.9-1.2 4" />
    </svg>
  );
}

export function HandsIcon({ className = "h-5 w-5" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M8 13 4.5 9.5a1.6 1.6 0 0 1 2.3-2.3L10 10.4M16 13l3.5-3.5a1.6 1.6 0 0 0-2.3-2.3L14 10.4" />
      <path d="M10 10.4 12 12.4l2-2M7 15l3 3 2 2 2-2 3-3" />
    </svg>
  );
}

// ---------------------------------------------------------------- layout

const NAV = [
  { href: "/login", label: "Sign in" },
  { href: "/assist", label: "Assisted sign-in" },
  { href: "/recover", label: "Account recovery" },
];

export function SiteHeader() {
  return (
    <header className="relative z-20 border-b border-slate-800 bg-[#0b0f19]/90 backdrop-blur-md">
      <div className="mx-auto grid h-[54px] max-w-4xl grid-cols-[1fr_auto] items-center gap-6 px-5 sm:grid-cols-[1fr_auto_1fr]">
        <Brand />
        <nav className="hidden items-center justify-center gap-7 sm:flex" aria-label="Main navigation">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="text-[13px] font-medium text-slate-300 transition hover:text-white"
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center justify-end gap-3">
          <Link
            href="/register"
            className="inline-flex items-center rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-blue-500 shadow-sm"
          >
            Create account
          </Link>
        </div>
      </div>
    </header>
  );
}

export function Shell({ children, wide = false, header, mainClassName }) {
  return (
    <div className="cyber-shell min-h-screen bg-[#0b0f19] text-slate-100">
      {header ?? <SiteHeader />}
      <main
        className={
          mainClassName ?? `kv-rise mx-auto px-4 py-12 sm:px-6 ${wide ? "max-w-5xl" : "max-w-md"}`
        }
      >
        {children}
      </main>
    </div>
  );
}

export function Card({ children, className = "" }) {
  return (
    <section
      className={`rounded-2xl border border-slate-800 bg-[#111827] p-7 shadow-lg shadow-black/25 sm:p-8 ${className}`}
    >
      {children}
    </section>
  );
}

export function H1({ children, className = "" }) {
  return (
    <h1 className={`font-display text-[24px] font-bold tracking-tight text-white sm:text-[26px] ${className}`}>
      {children}
    </h1>
  );
}

export function Muted({ children, className = "" }) {
  return <p className={`text-sm text-slate-400 leading-relaxed ${className}`}>{children}</p>;
}

// ---------------------------------------------------------------- controls

const VARIANTS = {
  primary:
    "bg-blue-600 hover:bg-blue-500 text-white font-medium shadow-sm transition active:scale-[0.99]",
  secondary:
    "border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition",
  ghost: "text-slate-300 hover:bg-slate-800 hover:text-white transition",
  danger: "border border-red-500/30 bg-red-500/10 text-red-200 hover:bg-red-500/20 transition",
  teal: "bg-blue-600 hover:bg-blue-500 text-white font-medium shadow-sm transition",
};

export function Button({
  variant = "primary",
  loading = false,
  className = "",
  children,
  disabled,
  ...rest
}) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}

export function Spinner() {
  return (
    <span
      className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
      aria-hidden="true"
    />
  );
}

export function Field({ label, hint, ...rest }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold text-slate-300">
        {label}
      </span>
      <input
        {...rest}
        className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
      />
      {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    </label>
  );
}

export function Alert({ kind = "error", children }) {
  const styles = {
    error: "border-red-500/30 bg-red-950/20 text-red-200",
    info: "border-slate-700 bg-slate-800/50 text-slate-300",
    success: "border-emerald-500/30 bg-emerald-950/20 text-emerald-200",
    warn: "border-amber-500/30 bg-amber-950/20 text-amber-200",
  }[kind];
  return (
    <div
      role="alert"
      className={`rounded-xl border px-3.5 py-2.5 text-xs font-medium ${styles}`}
    >
      {children}
    </div>
  );
}

export function Badge({ children, tone = "mist" }) {
  const styles = {
    mist: "border-slate-700 bg-slate-800 text-slate-300",
    teal: "border-blue-500/30 bg-blue-500/10 text-blue-400",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    danger: "border-red-500/30 bg-red-500/10 text-red-300",
    success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    violet: "border-violet-400/30 bg-violet-400/10 text-violet-300",
  }[tone];
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide ${styles}`}
    >
      {children}
    </span>
  );
}

export function Divider({ label }) {
  return (
    <div className="my-5 flex items-center gap-3 text-xs uppercase tracking-wider text-slate-500">
      <span className="h-px flex-1 bg-slate-800" />
      <span>{label}</span>
      <span className="h-px flex-1 bg-slate-800" />
    </div>
  );
}

export function formatTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
