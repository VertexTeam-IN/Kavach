"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import {
  Alert,
  Button,
  Card,
  Divider,
  FingerprintIcon,
  H1,
  KeyIcon,
  Muted,
  Shell,
} from "@/components/ui";
import { api, go } from "@/lib/api";
import { friendly } from "@/lib/errors";
import { loginWithPasskey } from "@/lib/webauthn";

function LoginInner() {
  const router = useRouter();
  const params = useSearchParams();
  const req = params.get("req");
  const then = params.get("then");
  const [info, setInfo] = useState(null);
  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [hostWarning, setHostWarning] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
      setHostWarning(true);
    }
  }, []);

  useEffect(() => {
    if (req)
      api(`/api/oidc/request/${req}`)
        .then(setInfo)
        .catch((e) => setError(friendly(e)));
    api("/api/me")
      .then((m) => setMe(m.is_assisted ? null : m))
      .catch(() => setMe(null));
  }, [req]);

  async function signIn() {
    setError(null);
    setBusy(true);
    try {
      const res = await loginWithPasskey(req);
      go(then && !req ? then : res.next, router.push);
    } catch (e) {
      setError(friendly(e));
      setBusy(false);
    }
  }

  async function continueAsMe() {
    setBusy(true);
    try {
      const res = await api("/api/oidc/continue", { method: "POST", body: { req } });
      go(res.redirect, router.push);
    } catch (e) {
      setError(friendly(e));
      setBusy(false);
    }
  }

  const q = req ? `?req=${req}` : "";

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
              href={`http://localhost:3000/login${q}`}
              className="mt-2 inline-block font-semibold text-white underline"
            >
              Switch to http://localhost:3000 →
            </a>
          </div>
        )}

        {/* Clean, Tasteful Security Icon */}
        <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-400">
          <FingerprintIcon className="h-6 w-6" />
        </div>

        {/* Title & Description */}
        <H1>{info ? `Sign in to ${info.client_name}` : "Sign in to Kavach"}</H1>
        <Muted className="mt-1.5">
          {info
            ? `${info.client_name} uses Kavach for passkey authentication. Use your device's biometrics or PIN.`
            : "Use the fingerprint, face recognition, or PIN you use to unlock this device."}
        </Muted>

        {/* Connected Client Metadata (if OIDC request) */}
        {info && (
          <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Application:</span>
              <span className="font-semibold text-white">{info.client_name}</span>
            </div>
            <div className="mt-1.5 flex items-center justify-between">
              <span className="text-slate-400">Assisted Sign-In:</span>
              <span className={info.allow_assisted ? "text-emerald-400 font-medium" : "text-slate-400"}>
                {info.allow_assisted ? "Allowed (View-only)" : "Disabled"}
              </span>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4">
            <Alert>{error}</Alert>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 space-y-2.5">
          {me && req && (
            <Button variant="teal" className="w-full" onClick={continueAsMe} loading={busy}>
              Continue as {me.display_name} →
            </Button>
          )}
          <Button className="w-full" onClick={signIn} loading={busy && !me}>
            <KeyIcon /> {busy ? "Waiting for device…" : "Sign in with passkey"}
          </Button>
        </div>

        <Divider label="or" />

        <div className="space-y-2.5 text-xs text-slate-300">
          <p>
            New to Kavach?{" "}
            <Link href={`/register${q}`} className="font-medium text-blue-400 hover:text-blue-300">
              Create an account
            </Link>
          </p>

          {(!info || info.allow_assisted) && (
            <p>
              Can&apos;t use a passkey?{" "}
              <Link href={`/assist${q}`} className="font-medium text-blue-400 hover:text-blue-300">
                Get help signing in
              </Link>
            </p>
          )}

          <p>
            <Link href="/recover" className="text-slate-400 hover:text-slate-200">
              Lost your device? Recover account
            </Link>
          </p>
        </div>
      </Card>
    </Shell>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginInner />
    </Suspense>
  );
}
