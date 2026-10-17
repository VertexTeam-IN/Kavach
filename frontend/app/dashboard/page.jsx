"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Brand, Button, KeyIcon, Shell, Spinner, formatTime } from "@/components/ui";
import { api } from "@/lib/api";
import { friendly } from "@/lib/errors";
import { addBackupPasskey } from "@/lib/webauthn";

function deviceName(ua) {
  if (!ua) return "Unknown device";
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /Chrome\//.test(ua)
      ? "Chrome"
      : /Firefox\//.test(ua)
        ? "Firefox"
        : /Safari\//.test(ua)
          ? "Safari"
          : "Browser";
  const os = /Windows/.test(ua)
    ? "Windows"
    : /Android/.test(ua)
      ? "Android"
      : /iPhone|iPad/.test(ua)
        ? "iOS"
        : /Mac OS/.test(ua)
          ? "macOS"
          : /Linux/.test(ua)
            ? "Linux"
            : "";
  return `${browser}${os ? ` on ${os}` : ""}`;
}

// ---------------------------------------------------------------- dashboard-only building blocks

function DashHeader({ me, onLogout }) {
  return (
    <header className="border-b border-slate-800 bg-[#0b0f19]">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-4">
          <Brand />
          <span className="hidden h-5 w-px bg-slate-800 sm:block" />
          <span className="hidden text-[13px] font-medium text-slate-400 sm:block">Account</span>
        </div>
        {me && (
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-[13px] font-medium leading-tight text-slate-200">{me.display_name}</p>
              <p className="text-[11px] leading-tight text-slate-500">@{me.username}</p>
            </div>
            <span className="grid h-8 w-8 place-items-center rounded-md bg-slate-800 text-xs font-semibold text-slate-200">
              {(me.display_name || me.username || "?").charAt(0).toUpperCase()}
            </span>
            <button
              onClick={onLogout}
              className="rounded-md px-2.5 py-1.5 text-[13px] text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

function Panel({ title, description, action, children, className = "" }) {
  return (
    <section className={`rounded-lg border border-slate-800 bg-[#0f1523] ${className}`}>
      <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
        </div>
        {action}
      </div>
      <div className="px-5">{children}</div>
    </section>
  );
}

function Stat({ label, value, note, tone = "default" }) {
  const dot = {
    default: "bg-slate-500",
    ok: "bg-emerald-500",
    warn: "bg-amber-500",
  }[tone];
  return (
    <div className="px-5 py-4">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums text-slate-100">{value}</p>
      <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-400">
        <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
        {note}
      </p>
    </div>
  );
}

function Tag({ children, tone = "default" }) {
  const styles = {
    default: "bg-slate-800 text-slate-300",
    blue: "bg-blue-500/10 text-blue-300",
    amber: "bg-amber-500/10 text-amber-300",
    green: "bg-emerald-500/10 text-emerald-300",
    red: "bg-red-500/10 text-red-300",
  }[tone];
  return (
    <span className={`ml-2 inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium ${styles}`}>
      {children}
    </span>
  );
}

function Notice({ tone = "info", title, children, action }) {
  const styles = {
    info: "border-slate-700 bg-slate-900/60",
    warn: "border-amber-500/30 bg-amber-500/5",
    error: "border-red-500/30 bg-red-500/5",
    success: "border-emerald-500/30 bg-emerald-500/5",
  }[tone];
  const bar = {
    info: "bg-blue-500",
    warn: "bg-amber-500",
    error: "bg-red-500",
    success: "bg-emerald-500",
  }[tone];
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`relative flex flex-wrap items-center justify-between gap-4 overflow-hidden rounded-lg border py-3 pl-5 pr-4 ${styles}`}
    >
      <span className={`absolute inset-y-0 left-0 w-0.5 ${bar}`} />
      <div className="min-w-0">
        {title && <p className="text-sm font-medium text-slate-100">{title}</p>}
        <div className="text-[13px] text-slate-400">{children}</div>
      </div>
      {action}
    </div>
  );
}

const smallBtn = "px-3 py-1.5 text-xs rounded-md";
const removeBtn =
  "rounded-md px-2.5 py-1 text-xs font-medium text-slate-400 transition hover:bg-red-500/10 hover:text-red-300 disabled:opacity-50";
const quietBtn =
  "rounded-md px-2.5 py-1 text-xs font-medium text-slate-400 transition hover:bg-slate-800 hover:text-slate-100 disabled:opacity-50";

function ScoreMeter({ score, level }) {
  const tone = { strong: "bg-emerald-500", good: "bg-blue-500", weak: "bg-amber-500" }[level];
  const tag = { strong: "green", good: "blue", weak: "amber" }[level];
  return (
    <div>
      <div className="flex items-end gap-3">
        <p className="text-3xl font-semibold tabular-nums text-slate-50">
          {score}
          <span className="text-base font-medium text-slate-500">/100</span>
        </p>
        <Tag tone={tag}>{level.charAt(0).toUpperCase() + level.slice(1)}</Tag>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full rounded-full ${tone} transition-all duration-500`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

function AlertRow({ a, readOnly, busy, onMe, onNotMe }) {
  const [confirm, setConfirm] = useState(false);
  const bar = a.severity === "warn" && !a.resolution ? "bg-amber-500" : "bg-slate-700";
  return (
    <li className="relative py-3 pl-4">
      <span className={`absolute inset-y-3 left-0 w-0.5 rounded-full ${bar}`} />
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-200">
            {!a.read && <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-blue-500 align-middle" />}
            {a.title}
            {a.resolution === "me" && <Tag>You confirmed</Tag>}
            {a.resolution === "not_me" && <Tag tone="red">Reported · secured</Tag>}
          </p>
          <p className="mt-0.5 text-xs text-slate-400">{a.detail}</p>
          <p className="mt-0.5 text-[11px] text-slate-500">
            {formatTime(a.at)}
            {a.ip ? ` · ${a.ip}` : ""}
          </p>
        </div>
        {a.can_report && !readOnly && (
          <div className="flex shrink-0 items-center gap-1">
            {confirm ? (
              <>
                <span className="mr-1 text-[11px] text-slate-400">Sign out other devices?</span>
                <button className={removeBtn} disabled={busy} onClick={onNotMe}>
                  {busy ? "Securing…" : "Yes, secure my account"}
                </button>
                <button className={quietBtn} onClick={() => setConfirm(false)}>
                  Cancel
                </button>
              </>
            ) : (
              <>
                <button className={quietBtn} disabled={busy} onClick={onMe}>
                  This was me
                </button>
                <button className={removeBtn} disabled={busy} onClick={() => setConfirm(true)}>
                  This wasn&apos;t me
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

// ---------------------------------------------------------------- page

export default function Dashboard() {
  const router = useRouter();
  const [me, setMe] = useState(null);
  const [passkeys, setPasskeys] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [audit, setAudit] = useState([]);
  const [sites, setSites] = useState([]);
  const [pending, setPending] = useState([]);
  const [alerts, setAlerts] = useState({ unread: 0, open_warnings: 0, items: [] });
  const [score, setScore] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(null);
  const [newCode, setNewCode] = useState(null);

  const load = useCallback(async () => {
    try {
      const m = await api("/api/me");
      setMe(m);
      const [p, s, a, c, al, sc] = await Promise.all([
        api("/api/passkeys"),
        api("/api/sessions"),
        api("/api/audit"),
        api("/api/connected-sites"),
        api("/api/alerts"),
        api("/api/security-score"),
      ]);
      setPasskeys(p);
      setSessions(s);
      setAudit(a);
      setSites(c);
      setAlerts(al);
      setScore(sc);
      if (!m.is_assisted) setPending(await api("/api/helpers/requests"));
    } catch (e) {
      if (e.status === 401) router.push("/login?then=/dashboard");
      else setError(friendly(e));
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  // Helpers: keep checking for people who need you
  useEffect(() => {
    if (!me || me.is_assisted) return;
    const t = setInterval(
      () =>
        api("/api/helpers/requests")
          .then(setPending)
          .catch(() => {}),
      4000,
    );
    return () => clearInterval(t);
  }, [me]);

  async function run(key, fn, ok) {
    setError(null);
    setNotice(null);
    setBusy(key);
    try {
      const res = await fn();
      if (ok) setNotice(typeof ok === "function" ? ok(res) : ok);
      await load();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(null);
    }
  }

  async function logout() {
    await api("/api/logout", { method: "POST" }).catch(() => {});
    router.push("/");
  }

  const layout = "mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10";

  if (!me) {
    return (
      <Shell header={<DashHeader />} mainClassName={layout}>
        {error ? (
          <Notice tone="error">{error}</Notice>
        ) : (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Spinner /> Loading your account…
          </div>
        )}
      </Shell>
    );
  }

  const readOnly = me.is_assisted;
  const addPasskey = (label) => run("backup", () => addBackupPasskey(label), "Passkey added.");

  return (
    <Shell header={<DashHeader me={me} onLogout={logout} />} mainClassName={layout}>
      {/* Page heading */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-50">Security overview</h1>
          <p className="mt-1 text-sm text-slate-400">
            Manage how you sign in, where you&apos;re signed in, and who can help you recover access.
          </p>
        </div>
        {!readOnly && (
          <Link href="/helpers">
            <Button variant="secondary" className={smallBtn}>
              Trusted helpers
            </Button>
          </Link>
        )}
      </div>

      {/* Notices */}
      <div className="mt-6 space-y-3 empty:hidden">
        {readOnly && (
          <Notice tone="warn" title="Assisted session · view only">
            Approved by {me.assisted_by ?? "your helper"}. Passkeys, helpers and recovery can&apos;t be
            changed. Expires {formatTime(me.session_expires_at)}.
          </Notice>
        )}
        {!readOnly && !me.has_backup && (
          <Notice
            tone="warn"
            title={passkeys.length === 0 ? "No active passkeys" : "Only one passkey registered"}
            action={
              <Button
                className={smallBtn}
                loading={busy === "backup"}
                onClick={() => addPasskey(passkeys.length === 0 ? "This device" : "Backup passkey")}
              >
                <KeyIcon className="h-3.5 w-3.5" />
                {passkeys.length === 0 ? "Create passkey" : "Add backup passkey"}
              </Button>
            }
          >
            {passkeys.length === 0
              ? "You recovered your account with your recovery code. Create a passkey on this device for passwordless sign-in."
              : "If you lose this device you could be locked out. Add your phone as a backup."}
          </Notice>
        )}
        {pending.map((r) => (
          <Notice
            key={r.id}
            tone="info"
            title="Sign-in assistance requested"
            action={
              <Link href={`/assist/approve/${r.id}`}>
                <Button className={smallBtn}>Review request</Button>
              </Link>
            }
          >
            <span className="text-slate-200">{r.owner.display_name}</span> is asking for help signing
            in to {r.website}.
          </Notice>
        ))}
        {error && <Notice tone="error">{error}</Notice>}
        {notice && <Notice tone="success">{notice}</Notice>}
      </div>

      {/* Summary */}
      <div className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-slate-800 bg-slate-800 lg:grid-cols-4 [&>*]:bg-[#0f1523]">
        <Stat
          label="Passkeys"
          value={passkeys.length}
          note={me.has_backup ? "Backup in place" : "No backup"}
          tone={me.has_backup ? "ok" : "warn"}
        />
        <Stat label="Active sessions" value={sessions.length} note="Across your devices" />
        <Stat label="Connected websites" value={sites.length} note="Using Kavach sign-in" />
        <Stat
          label="Recovery code"
          value={me.has_recovery_code ? "Set" : "None"}
          note={me.has_recovery_code ? "Unused and valid" : "Create one"}
          tone={me.has_recovery_code ? "ok" : "warn"}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <Panel title="Security score" description="How well your account is protected, and what to fix.">
          {score ? (
            <div className="space-y-4 py-4">
              <ScoreMeter score={score.score} level={score.level} />
              <ul className="space-y-2.5">
                {score.checks.map((c) => (
                  <li key={c.id} className="flex items-start gap-2.5">
                    <span
                      className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded-full text-[10px] font-bold ${
                        c.ok ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"
                      }`}
                      aria-hidden="true"
                    >
                      {c.ok ? "✓" : "!"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="flex items-center justify-between gap-2 text-[13px] text-slate-200">
                        {c.label}
                        <span className="shrink-0 text-[11px] tabular-nums text-slate-500">
                          {c.ok ? `+${c.points}` : `0 / ${c.points}`}
                        </span>
                      </p>
                      {!c.ok && (
                        <p className="mt-0.5 text-xs text-slate-500">
                          {c.fix}{" "}
                          {!readOnly && c.id === "backup" && (
                            <button
                              className="font-medium text-blue-400 hover:text-blue-300"
                              onClick={() => addPasskey("Backup passkey")}
                            >
                              Add one
                            </button>
                          )}
                          {!readOnly && c.id === "helper" && (
                            <Link href="/helpers" className="font-medium text-blue-400 hover:text-blue-300">
                              Invite a helper
                            </Link>
                          )}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="py-6 text-center text-xs text-slate-500">Calculating…</p>
          )}
        </Panel>

        <Panel
          title={
            <span className="flex items-center">
              Security alerts
              {alerts.unread > 0 && <Tag tone="blue">{alerts.unread} new</Tag>}
            </span>
          }
          description="New devices, new passkeys, recovery and assisted sign-ins. Tell us if it wasn't you."
          action={
            !readOnly &&
            alerts.unread > 0 && (
              <button
                className={quietBtn}
                disabled={busy === "read"}
                onClick={() => run("read", () => api("/api/alerts/read", { method: "POST" }))}
              >
                Mark all read
              </button>
            )
          }
        >
          {alerts.items.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-500">
              No alerts. We&apos;ll tell you here when something changes on your account.
            </p>
          ) : (
            <ul className="max-h-[22rem] divide-y divide-slate-800/80 overflow-y-auto">
              {alerts.items.map((a) => (
                <AlertRow
                  key={a.id}
                  a={a}
                  readOnly={readOnly}
                  busy={busy === a.id}
                  onMe={() =>
                    run(a.id, () => api(`/api/alerts/${a.id}/me`, { method: "POST" }), "Marked as you. Thanks for checking.")
                  }
                  onNotMe={() =>
                    run(
                      a.id,
                      () => api(`/api/alerts/${a.id}/not-me`, { method: "POST" }),
                      (r) => `Account secured: ${r.done.join(" · ")}.`,
                    )
                  }
                />
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel
          title="Passkeys"
          description="Devices that can sign you in with fingerprint, face or PIN."
          action={
            !readOnly &&
            (me.has_backup || passkeys.length === 0) && (
              <Button
                variant="secondary"
                className={smallBtn}
                loading={busy === "backup"}
                onClick={() => addPasskey(passkeys.length === 0 ? "This device" : "Another device")}
              >
                Add passkey
              </Button>
            )
          }
        >
          <ul className="divide-y divide-slate-800/80">
            {passkeys.length === 0 && (
              <li className="py-6 text-center text-xs text-slate-500">No passkeys registered yet.</li>
            )}
            {passkeys.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-3 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-slate-800 text-slate-400">
                    <KeyIcon className="h-3.5 w-3.5" />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-200">
                      {p.label}
                      {p.synced && <Tag tone="blue">Synced</Tag>}
                      {p.stale && <Tag tone="amber">Unused 90+ days</Tag>}
                    </p>
                    <p className="text-xs text-slate-500">
                      {p.model && <span className="text-slate-400">{p.model} · </span>}
                      Added {formatTime(p.created_at)} · Last used {formatTime(p.last_used_at)}
                    </p>
                    {p.stale && (
                      <p className="mt-0.5 text-xs text-amber-300/80">
                        Old phone or laptop? Remove it if you no longer use it.
                      </p>
                    )}
                  </div>
                </div>
                {!readOnly && passkeys.length > 1 && (
                  <button
                    className={removeBtn}
                    disabled={busy === p.id}
                    onClick={() =>
                      run(
                        p.id,
                        () => api(`/api/passkeys/${p.id}`, { method: "DELETE" }),
                        "Passkey removed.",
                      )
                    }
                  >
                    {busy === p.id ? "Removing…" : "Remove"}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </Panel>

        <Panel
          title="Active sessions"
          description="Browsers currently signed in to your account."
          action={
            !readOnly &&
            sessions.length > 1 && (
              <Button
                variant="secondary"
                className={smallBtn}
                loading={busy === "others"}
                onClick={() =>
                  run(
                    "others",
                    () => api("/api/sessions/revoke-others", { method: "POST" }),
                    (r) => `Signed out ${r.signed_out} other session${r.signed_out === 1 ? "" : "s"}.`,
                  )
                }
              >
                Sign out all others
              </Button>
            )
          }
        >
          <ul className="divide-y divide-slate-800/80">
            {sessions.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">
                    {deviceName(s.user_agent)}
                    {s.current && <Tag tone="blue">This device</Tag>}
                    {s.acr.endsWith("assisted") && <Tag tone="amber">Assisted</Tag>}
                  </p>
                  <p className="text-xs text-slate-500">Signed in {formatTime(s.created_at)}</p>
                </div>
                {!readOnly && !s.current && (
                  <button
                    className={removeBtn}
                    disabled={busy === s.id}
                    onClick={() =>
                      run(
                        s.id,
                        () => api(`/api/sessions/${s.id}`, { method: "DELETE" }),
                        "Session signed out.",
                      )
                    }
                  >
                    {busy === s.id ? "Signing out…" : "Sign out"}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="Connected websites" description="Sites you've allowed to use Kavach sign-in.">
          {sites.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-500">
              No websites yet. Use “Continue with Kavach” on a website to connect it.
            </p>
          ) : (
            <ul className="divide-y divide-slate-800/80">
              {sites.map((s) => (
                <li key={s.client_id} className="flex items-center justify-between gap-3 py-3">
                  <p className="truncate text-sm font-medium text-slate-200">{s.name}</p>
                  <p className="shrink-0 text-xs text-slate-500">Allowed {formatTime(s.granted_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Recovery code"
          description="A one-time code to regain access if you lose all your passkeys."
        >
          <div className="space-y-4 py-4">
            <p className="text-sm text-slate-400">
              {me.has_recovery_code
                ? "You have an unused recovery code on file."
                : "You don't have a recovery code. Create one and store it somewhere safe."}
            </p>
            {newCode && (
              <div className="rounded-md border border-slate-700 bg-slate-950 px-4 py-3">
                <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
                  New recovery code — save it now
                </p>
                <p className="mt-1 select-all font-mono text-lg tracking-wider text-slate-100">{newCode}</p>
              </div>
            )}
            {!readOnly && (
              <Button
                variant="secondary"
                className={smallBtn}
                loading={busy === "code"}
                onClick={() =>
                  run(
                    "code",
                    async () => {
                      const r = await api("/api/recovery-code", { method: "POST" });
                      setNewCode(r.recovery_code);
                    },
                    "New recovery code created. The old one no longer works — save this one.",
                  )
                }
              >
                {me.has_recovery_code ? "Replace recovery code" : "Create recovery code"}
              </Button>
            )}
          </div>
        </Panel>
      </div>

      <Panel
        className="mt-6"
        title="Recent security activity"
        description="The latest sign-ins and account changes."
      >
        {audit.length === 0 ? (
          <p className="py-6 text-center text-xs text-slate-500">No activity yet.</p>
        ) : (
          <div className="-mx-5 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs text-slate-500">
                  <th className="px-5 py-2.5 font-medium">Event</th>
                  <th className="px-5 py-2.5 font-medium">Website</th>
                  <th className="px-5 py-2.5 font-medium">By</th>
                  <th className="px-5 py-2.5 text-right font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 border-t border-slate-800">
                {audit.slice(0, 15).map((a) => (
                  <tr key={a.id}>
                    <td className="px-5 py-2.5 text-slate-200">{a.label}</td>
                    <td className="px-5 py-2.5 text-slate-400">{a.website ?? "—"}</td>
                    <td className="px-5 py-2.5 text-slate-400">{a.by ?? "—"}</td>
                    <td className="whitespace-nowrap px-5 py-2.5 text-right text-xs text-slate-500">
                      {formatTime(a.at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </Shell>
  );
}
