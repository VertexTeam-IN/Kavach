"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Alert, Button, Card, H1, Muted, Shell } from "@/components/ui";
import { api, go } from "@/lib/api";
import { friendly } from "@/lib/errors";

function ConsentInner() {
  const router = useRouter();
  const req = useSearchParams().get("req");
  const [info, setInfo] = useState(null);
  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    if (!req) return setError("Missing sign-in request.");
    api(`/api/oidc/request/${req}`)
      .then(setInfo)
      .catch((e) => setError(friendly(e)));
    api("/api/me")
      .then(setMe)
      .catch(() => router.push(`/login?req=${req}`));
  }, [req, router]);

  async function decide(allow) {
    setBusy(allow ? "allow" : "deny");
    try {
      const res = await api("/api/oidc/consent", { method: "POST", body: { req, allow } });
      go(res.redirect, router.push);
    } catch (e) {
      setError(friendly(e));
      setBusy(null);
    }
  }

  return (
    <Shell>
      <Card>
        {error && <Alert>{error}</Alert>}
        {info && me && (
          <>
            <H1>Allow {info.client_name}?</H1>
            <Muted className="mt-2">
              Signed in as <b className="text-ink">{me.display_name}</b> (@{me.username})
            </Muted>
            <div className="mt-6 rounded-2xl bg-mist p-5">
              <p className="mb-3 text-sm font-semibold text-ink">
                {info.client_name} will receive:
              </p>
              <ul className="space-y-2">
                {info.scopes.map((s) => (
                  <li key={s} className="flex items-center gap-2 text-sm text-slate">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-teal text-xs text-white">
                      ✓
                    </span>
                    {s}
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-xs text-slate">
                Never your passkey, fingerprint, face or PIN.
              </p>
            </div>
            <div className="mt-7 grid grid-cols-2 gap-3">
              <Button
                variant="secondary"
                onClick={() => decide(false)}
                loading={busy === "deny"}
                disabled={!!busy}
              >
                Cancel
              </Button>
              <Button onClick={() => decide(true)} loading={busy === "allow"} disabled={!!busy}>
                Allow
              </Button>
            </div>
          </>
        )}
      </Card>
    </Shell>
  );
}

export default function ConsentPage() {
  return (
    <Suspense>
      <ConsentInner />
    </Suspense>
  );
}
