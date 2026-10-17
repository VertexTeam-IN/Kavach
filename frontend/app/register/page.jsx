"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import {
  Alert,
  Button,
  Card,
  Divider,
  Field,
  H1,
  KeyIcon,
  Muted,
  Shell,
  ShieldIcon,
} from "@/components/ui";
import { go } from "@/lib/api";
import { friendly } from "@/lib/errors";
import { registerPasskey } from "@/lib/webauthn";

function RegisterInner() {
  const router = useRouter();
  const req = useSearchParams().get("req");
  const [form, setForm] = useState({ username: "", display_name: "", phone: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  const [hostWarning, setHostWarning] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
      setHostWarning(true);
    }
  }, []);

  async function submit(e) {
    e.preventDefault();
    setError(null);

    // Client-side sanitization and validation
    const cleanUser = form.username.trim().toLowerCase().replace(/^@/, "");
    const cleanDisplay = form.display_name.trim();
    const cleanPhone = form.phone.trim().replace(/[\s\-\(\)\.]/g, "");

    if (cleanUser.length < 3) {
      setError("Username must be at least 3 characters long.");
      return;
    }
    if (!/^[a-z0-9_.-]+$/.test(cleanUser)) {
      setError("Username can only contain lowercase letters, numbers, dots, and dashes.");
      return;
    }
    if (!cleanDisplay) {
      setError("Please enter your full name.");
      return;
    }
    if (cleanPhone.length < 6) {
      setError("Please enter a valid mobile number (at least 6 digits).");
      return;
    }

    setBusy(true);
    try {
      const res = await registerPasskey(
        {
          username: cleanUser,
          display_name: cleanDisplay,
          phone: cleanPhone,
        },
        req,
      );
      setDone({ code: res.recovery_code, next: res.next });
    } catch (err) {
      setError(friendly(err));
    } finally {
      setBusy(false);
    }
  }

  const copyCode = async () => {
    if (!done?.code) return;
    try {
      await navigator.clipboard.writeText(done.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // fallback
    }
  };

  const q = req ? `?req=${req}` : "";

  if (done) {
    return (
      <Shell>
        <Card>
          <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-400">
            <ShieldIcon className="h-6 w-6" />
          </div>

          <H1>Passkey created ✓</H1>
          <Muted className="mt-1.5">
            Your passkey is stored on this device. Save your emergency recovery code below in a safe place.
          </Muted>

          {/* Clean Emergency Recovery Credential Box */}
          <div className="my-5 rounded-xl border border-slate-700 bg-slate-900 p-4">
            <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
              <span>Recovery code</span>
              <span className="text-[11px] text-slate-500">One-time display</span>
            </div>

            <div className="mt-2.5 flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-[#0b0f19] px-3.5 py-3">
              <span className="select-all font-mono text-lg font-bold tracking-wider text-amber-300">
                {done.code}
              </span>
              <button
                type="button"
                onClick={copyCode}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-medium text-slate-200 transition hover:bg-slate-700 hover:text-white"
              >
                {copied ? "Copied! ✓" : "Copy"}
              </button>
            </div>
          </div>

          <Alert kind="warn">
            Kavach only stores a scrambled hash and cannot regenerate this code. If you lose all your devices, this is the only way to recover access.
          </Alert>

          <label className="mt-5 flex cursor-pointer items-start gap-2.5 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={saved}
              onChange={(e) => setSaved(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded accent-blue-600 cursor-pointer"
            />
            <span>I have saved my recovery code in a secure location</span>
          </label>

          <Button
            className="mt-5 w-full"
            disabled={!saved}
            onClick={() => go(done.next, router.push)}
          >
            Continue →
          </Button>
        </Card>
      </Shell>
    );
  }

  return (
    <Shell>
      <Card>
        {/* Hostname Warning if accessed via 127.0.0.1 */}
        {hostWarning && (
          <div className="mb-5 rounded-xl border border-amber-500/30 bg-amber-950/20 p-3.5 text-xs text-amber-200">
            <p className="font-semibold text-amber-300">Notice: Open on localhost</p>
            <p className="mt-1">
              Passkeys require origin <code className="font-mono text-white">localhost:3000</code>.
            </p>
            <a
              href={`http://localhost:3000/register${q}`}
              className="mt-2 inline-block font-semibold text-white underline"
            >
              Switch to http://localhost:3000 →
            </a>
          </div>
        )}

        <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-400">
          <KeyIcon className="h-6 w-6" />
        </div>

        <H1>Create your Kavach account</H1>
        <Muted className="mt-1.5">
          No password. Your device will create a passkey protected by your fingerprint, face, or PIN.
        </Muted>

        <form onSubmit={submit} className="mt-6 space-y-3.5">
          <Field
            label="Username"
            required
            autoComplete="username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            placeholder="e.g. aditya.sharma"
            hint="Lowercase letters, numbers, dots or dashes (min 3 chars)"
          />

          <Field
            label="Full name"
            required
            autoComplete="name"
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            placeholder="e.g. Aditya Sharma"
          />

          <Field
            label="Mobile number"
            required
            type="tel"
            autoComplete="tel"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            placeholder="e.g. 9876543210 or +91 98765 43210"
            hint="Used only for assisted sign-in and account recovery"
          />

          {error && <Alert>{error}</Alert>}

          <Button type="submit" className="w-full mt-2" loading={busy}>
            <KeyIcon /> {busy ? "Creating passkey on device…" : "Create passkey"}
          </Button>
        </form>

        <Divider label="or" />

        <div className="text-center text-xs text-slate-400">
          Already have an account?{" "}
          <Link
            href={`/login${q}`}
            className="font-medium text-blue-400 hover:text-blue-300"
          >
            Sign in
          </Link>
        </div>
      </Card>
    </Shell>
  );
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterInner />
    </Suspense>
  );
}
