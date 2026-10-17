"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { Countdown, MatchCodeDisplay } from "@/components/assist";
import { Alert, Button, Card, Field, H1, HandsIcon, Muted, Shell } from "@/components/ui";
import { api, go } from "@/lib/api";
import { friendly } from "@/lib/errors";

function AssistInner() {
  const router = useRouter();
  const req = useSearchParams().get("req");
  const [info, setInfo] = useState(null);
  const [username, setUsername] = useState("");
  const [otp, setOtp] = useState("");
  const [started, setStarted] = useState(null);
  const [view, setView] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const completing = useRef(false);

  useEffect(() => {
    if (req)
      api(`/api/oidc/request/${req}`)
        .then(setInfo)
        .catch((e) => setError(friendly(e)));
  }, [req]);

  const headers = started ? { "X-Assist-Token": started.token } : undefined;

  const complete = useCallback(
    async (s) => {
      if (completing.current) return;
      completing.current = true;
      try {
        const res = await api(`/api/assist/${s.id}/complete`, {
          method: "POST",
          headers: { "X-Assist-Token": s.token },
        });
        go(res.redirect, router.push);
      } catch (e) {
        setError(friendly(e));
      }
    },
    [router],
  );

  // Poll while waiting for the helper
  useEffect(() => {
    if (!started || view?.status !== "awaiting_helper") return;
    const t = setInterval(async () => {
      try {
        const v = await api(`/api/assist/${started.id}`, {
          headers: { "X-Assist-Token": started.token },
        });
        setView(v);
        if (v.status === "approved") complete(started);
      } catch (e) {
        setError(friendly(e));
      }
    }, 2000);
    return () => clearInterval(t);
  }, [started, view?.status, complete]);

  async function start(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const s = await api("/api/assist", {
        method: "POST",
        body: { username: username.trim().toLowerCase(), req },
      });
      setStarted(s);
      if (s.demo_phone)
        window.open(
          `/mock-phone?phone=${encodeURIComponent(s.demo_phone)}`,
          "kavach-phone",
          "width=420,height=760",
        );
    } catch (err) {
      setError(friendly(err));
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp(e) {
    e.preventDefault();
    if (!started) return;
    setError(null);
    setBusy(true);
    try {
      setView(
        await api(`/api/assist/${started.id}/otp`, { method: "POST", headers, body: { otp } }),
      );
    } catch (err) {
      setError(friendly(err));
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (started)
      await api(`/api/assist/${started.id}/cancel`, { method: "POST", headers }).catch(() => {});
    router.push(req ? `/login?req=${req}` : "/");
  }

  const ended = view && ["rejected", "cancelled", "expired"].includes(view.status);

  return (
    <Shell>
      <Card>
        <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-teal text-white">
          <HandsIcon className="h-8 w-8" />
        </div>

        {/* Step 1 — who are you */}
        {!started && (
          <>
            <H1>Get help signing in</H1>
            <Muted className="mt-2">
              {info ? `Sign in to ${info.client_name} ` : "Sign in "}
              with help from someone you trust. They approve with their own passkey — they never get
              your account.
            </Muted>
            <form onSubmit={start} className="mt-7 space-y-4">
              <Field
                label="Your Kavach username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
              {error && <Alert>{error}</Alert>}
              <Button type="submit" className="w-full" loading={busy}>
                Send me a code
              </Button>
            </form>
          </>
        )}

        {/* Step 2 — OTP */}
        {started && !view && (
          <>
            <H1>Enter the code we sent</H1>
            <Muted className="mt-2">We sent a 6-digit code by SMS to {started.phone_hint}.</Muted>
            {started.demo_phone && (
              <p className="mt-2 text-sm">
                Demo:{" "}
                <a
                  className="font-semibold text-teal hover:underline"
                  target="kavach-phone"
                  href={`/mock-phone?phone=${encodeURIComponent(started.demo_phone)}`}
                >
                  open the simulated phone
                </a>
              </p>
            )}
            <form onSubmit={verifyOtp} className="mt-7 space-y-4">
              <Field
                label="SMS code"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                required
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              />
              {error && <Alert>{error}</Alert>}
              <Button type="submit" className="w-full" loading={busy}>
                Continue
              </Button>
            </form>
          </>
        )}

        {/* Step 3 — match number, waiting for helper */}
        {view && view.status === "awaiting_helper" && view.match_code && (
          <div className="text-center">
            <H1>Tell your helper this number</H1>
            <Muted className="mt-2">
              Ask them to open Kavach and pick this number, then approve with their passkey.
            </Muted>
            <div className="my-8">
              <MatchCodeDisplay code={view.match_code} />
            </div>
            <p className="text-sm text-slate">
              Signing in to <b className="text-ink">{view.website}</b>
            </p>
            <div className="mt-3 flex items-center justify-center gap-3">
              <span className="h-2 w-2 animate-pulse rounded-full bg-teal" />
              <span className="text-sm text-slate">Waiting for approval ·</span>
              <Countdown until={view.expires_at} />
            </div>
            {error && (
              <div className="mt-4">
                <Alert>{error}</Alert>
              </div>
            )}
          </div>
        )}

        {view && (view.status === "approved" || view.status === "consumed") && (
          <div className="text-center">
            <H1>Approved by {view.approved_by}</H1>
            <Muted className="mt-2">Signing you in…</Muted>
            {error && (
              <div className="mt-4">
                <Alert>{error}</Alert>
              </div>
            )}
          </div>
        )}

        {ended && (
          <div className="text-center">
            <H1>Request {view?.status}</H1>
            <Muted className="mt-2">
              {view?.status === "rejected"
                ? "Your helper declined this request."
                : "This request is no longer valid. You can start again."}
            </Muted>
            <Button className="mt-6" onClick={() => window.location.reload()}>
              Start again
            </Button>
          </div>
        )}

        {started && !ended && (
          <button
            onClick={cancel}
            className="mt-8 block w-full text-center text-sm text-slate hover:underline"
          >
            Cancel
          </button>
        )}
        {!started && (
          <p className="mt-6 text-sm">
            <Link
              href={req ? `/login?req=${req}` : "/login"}
              className="text-slate hover:underline"
            >
              ← Back to passkey sign-in
            </Link>
          </p>
        )}
      </Card>
    </Shell>
  );
}

export default function AssistPage() {
  return (
    <Suspense>
      <AssistInner />
    </Suspense>
  );
}
