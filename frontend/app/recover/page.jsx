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
import { api, go } from "@/lib/api";
import { friendly } from "@/lib/errors";

function RecoverInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const req = searchParams.get("req");

  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [done, setDone] = useState(null);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [hostWarning, setHostWarning] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
      setHostWarning(true);
    }
  }, []);

  async function handleRecover(e) {
    e.preventDefault();
    setError(null);

    const cleanUser = username.trim().toLowerCase().replace(/^@/, "");
    const cleanCode = code.trim().toUpperCase();

    if (!cleanUser) {
      setError("Please enter your username.");
      return;
    }
    if (!cleanCode) {
      setError("Please enter your recovery code.");
      return;
    }

    setBusy(true);
    try {
      const res = await api("/api/recovery/recover", {
        method: "POST",
        body: { username: cleanUser, code: cleanCode, req },
      });
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

  // Step 2: Account recovered, display new recovery code
  if (done) {
    return (
      <Shell>
        <Card>
          <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-400">
            <ShieldIcon className="h-6 w-6" />
          </div>

          <H1>Account recovered ✓</H1>
          <Muted className="mt-1.5">
            Your account has been recovered. All previous sessions and passkeys have been revoked.
            Save your NEW emergency recovery code below.
          </Muted>

          {/* New Emergency Recovery Code Box */}
          <div className="my-5 rounded-xl border border-slate-700 bg-slate-900 p-4">
            <div className="flex items-center justify-between text-xs font-medium text-slate-400">
              <span>Your NEW recovery code</span>
              <span className="text-[11px] text-slate-500">One-time display</span>
            </div>

            <div className="mt-2.5 flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-[#0b0f19] px-3.5 py-3">
              <span className="select-all font-mono text-lg font-bold tracking-wider text-amber-300">
                {done.code}
              </span>
              <button
                type="button"
                onClick={copyCode}
                className="cursor-pointer rounded-md border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-medium text-slate-200 transition hover:bg-slate-700 hover:text-white"
              >
                {copied ? "Copied! ✓" : "Copy"}
              </button>
            </div>
          </div>

          <Alert kind="warn">
            Your old recovery code no longer works. Save this new code securely in a safe place.
          </Alert>

          <label className="mt-5 flex cursor-pointer items-start gap-2.5 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={saved}
              onChange={(e) => setSaved(e.target.checked)}
              className="mt-0.5 h-4 w-4 cursor-pointer rounded accent-blue-600"
            />
            <span>I have saved my new recovery code in a secure location</span>
          </label>

          <Button
            className="mt-5 w-full"
            disabled={!saved}
            onClick={() => go(done.next || "/dashboard", router.push)}
          >
            Go to dashboard →
          </Button>
        </Card>
      </Shell>
    );
  }

  // Step 1: Username + Recovery Code form
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
              href={`http://localhost:3000/recover${q}`}
              className="mt-2 inline-block font-semibold text-white underline"
            >
              Switch to http://localhost:3000 →
            </a>
          </div>
        )}

        <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-400">
          <KeyIcon className="h-6 w-6" />
        </div>

        <H1>Recover your account</H1>
        <Muted className="mt-1.5">
          Lost your device? Enter your username and the recovery code you saved when setting up your account.
        </Muted>

        <form onSubmit={handleRecover} className="mt-6 space-y-4">
          <Field
            label="Username"
            required
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g. aditya.sharma"
          />

          <Field
            label="Recovery code"
            required
            placeholder="KVCH-XXXX-XXXX-XXXX"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            hint="The code provided when you created your account"
          />

          {error && <Alert>{error}</Alert>}

          <Button type="submit" className="mt-2 w-full" loading={busy}>
            Recover account
          </Button>
        </form>

        <Divider label="or" />

        <div className="space-y-2.5 text-xs text-slate-300">
          <p>
            Remember your passkey?{" "}
            <Link href={`/login${q}`} className="font-medium text-blue-400 hover:text-blue-300">
              Sign in
            </Link>
          </p>

          <p>
            Can&apos;t use a passkey?{" "}
            <Link href={`/assist${q}`} className="font-medium text-blue-400 hover:text-blue-300">
              Get help signing in
            </Link>
          </p>
        </div>
      </Card>
    </Shell>
  );
}

export default function RecoverPage() {
  return (
    <Suspense>
      <RecoverInner />
    </Suspense>
  );
}
