"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Countdown, MatchCodePicker } from "@/components/assist";
import { Alert, Button, Card, H1, HandsIcon, KeyIcon, Muted, Shell } from "@/components/ui";
import { api } from "@/lib/api";
import { friendly } from "@/lib/errors";
import { helperApprove, loginWithPasskey } from "@/lib/webauthn";

export default function ApprovePage() {
  const { id } = useParams();
  const router = useRouter();
  const [view, setView] = useState(null);
  const [needLogin, setNeedLogin] = useState(false);
  const [chosen, setChosen] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    try {
      setView(await api(`/api/assist/${id}/helper`));
      setNeedLogin(false);
    } catch (e) {
      const status = e.status;
      if (status === 401) setNeedLogin(true);
      else setError(friendly(e));
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function signIn() {
    setBusy("login");
    setError(null);
    try {
      await loginWithPasskey(null);
      await load();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(null);
    }
  }

  async function approve() {
    if (!chosen) return;
    setBusy("approve");
    setError(null);
    try {
      await helperApprove(id, chosen);
      await load();
    } catch (e) {
      setError(friendly(e));
      setChosen(null);
      await load();
    } finally {
      setBusy(null);
    }
  }

  async function reject() {
    setBusy("reject");
    try {
      await api(`/api/assist/${id}/reject`, { method: "POST" });
      await load();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Shell>
      <Card>
        <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-teal text-white">
          <HandsIcon className="h-8 w-8" />
        </div>

        {needLogin && (
          <>
            <H1>Sign in to help</H1>
            <Muted className="mt-2">Use your own passkey to see this request.</Muted>
            {error && (
              <div className="mt-4">
                <Alert>{error}</Alert>
              </div>
            )}
            <Button className="mt-6 w-full" onClick={signIn} loading={busy === "login"}>
              <KeyIcon /> Sign in with passkey
            </Button>
          </>
        )}

        {!needLogin && !view && error && <Alert>{error}</Alert>}

        {view && view.status === "awaiting_helper" && (
          <>
            <H1>{view.owner.display_name} needs help signing in</H1>
            <div className="mt-5 space-y-2 rounded-2xl bg-mist p-5 text-sm">
              <p>
                <span className="text-slate">Person:</span> <b>{view.owner.display_name}</b> (@
                {view.owner.username})
              </p>
              <p>
                <span className="text-slate">Website:</span> <b>{view.website}</b>
              </p>
              {view.scopes && view.scopes.length > 0 && (
                <p>
                  <span className="text-slate">Website will see:</span> {view.scopes.join(", ")}
                </p>
              )}
              <p>
                <span className="text-slate">Access:</span> one sign-in, view only, 15 minutes
              </p>
              <p className="flex items-center gap-2">
                <span className="text-slate">Time left:</span>{" "}
                <Countdown until={view.expires_at} onExpire={load} />
              </p>
            </div>

            <Alert kind="warn">
              Only approve if you are talking to {view.owner.display_name} right now and they asked
              you to.
            </Alert>

            <p className="mb-3 mt-6 font-semibold">Which number do they see on their screen?</p>
            <MatchCodePicker choices={view.choices ?? []} value={chosen} onChange={setChosen} />

            {error && (
              <div className="mt-4">
                <Alert>{error}</Alert>
              </div>
            )}

            <div className="mt-6 grid grid-cols-2 gap-3">
              <Button
                variant="secondary"
                onClick={reject}
                loading={busy === "reject"}
                disabled={!!busy}
              >
                Reject
              </Button>
              <Button
                variant="teal"
                onClick={approve}
                loading={busy === "approve"}
                disabled={!chosen || !!busy}
              >
                <KeyIcon /> Approve
              </Button>
            </div>
            <p className="mt-3 text-center text-xs text-slate">
              You&apos;ll confirm with your own fingerprint, face or PIN.
            </p>
          </>
        )}

        {view && view.status !== "awaiting_helper" && (
          <>
            <H1>
              {view.status === "approved" || view.status === "consumed"
                ? "Approved ✓"
                : `Request ${view.status}`}
            </H1>
            <Muted className="mt-2">
              {view.status === "approved" || view.status === "consumed"
                ? `${view.owner.display_name} can now sign in to ${view.website} — once, view only.`
                : "Nothing more to do."}
            </Muted>
            {error && (
              <div className="mt-4">
                <Alert>{error}</Alert>
              </div>
            )}
            <Link href="/dashboard">
              <Button variant="secondary" className="mt-6">
                Back to dashboard
              </Button>
            </Link>
          </>
        )}
      </Card>
      <p className="mt-4 text-center text-xs text-slate">
        <button onClick={() => router.push("/helpers")} className="hover:underline">
          Manage the people you help
        </button>
      </p>
    </Shell>
  );
}
