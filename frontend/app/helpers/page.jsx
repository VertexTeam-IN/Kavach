"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Alert, Badge, Button, Card, Field, H1, HandsIcon, Muted, Shell } from "@/components/ui";
import { api } from "@/lib/api";
import { friendly } from "@/lib/errors";

export default function HelpersPage() {
  const router = useRouter();
  const [data, setData] = useState(null);
  const [pending, setPending] = useState([]);
  const [username, setUsername] = useState("");
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    try {
      setData(await api("/api/helpers"));
      setPending(await api("/api/helpers/requests"));
    } catch (e) {
      if (e.status === 401) router.push("/login?then=/helpers");
      else setError(friendly(e));
    }
  }, [router]);

  useEffect(() => {
    load();
    const t = setInterval(
      () =>
        api("/api/helpers/requests")
          .then(setPending)
          .catch(() => {}),
      3000,
    );
    return () => clearInterval(t);
  }, [load]);

  async function run(key, fn, ok) {
    setError(null);
    setNotice(null);
    setBusy(key);
    try {
      await fn();
      setNotice(ok);
      await load();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(null);
    }
  }

  function invite(e) {
    e.preventDefault();
    run(
      "invite",
      () => api("/api/helpers/invite", { method: "POST", body: { username } }),
      `Invitation sent to @${username}.`,
    ).then(() => setUsername(""));
  }

  return (
    <Shell wide>
      <div className="mb-8 flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-teal text-white">
          <HandsIcon className="h-6 w-6" />
        </div>
        <div>
          <H1>Trusted helpers</H1>
          <Muted>
            A helper can approve ONE sign-in for you with their own passkey. They never get your
            account.
          </Muted>
        </div>
      </div>

      <div className="space-y-4">
        {error && <Alert>{error}</Alert>}
        {notice && <Alert kind="success">{notice}</Alert>}
        {pending.map((r) => (
          <div
            key={r.id}
            className="flex items-center justify-between gap-4 rounded-2xl border border-teal/40 bg-teal-soft p-5"
          >
            <span>
              <b>{r.owner.display_name}</b> wants to sign in to <b>{r.website}</b>
            </span>
            <Link href={`/assist/approve/${r.id}`}>
              <Button variant="teal">Review request</Button>
            </Link>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-1 text-lg font-bold">People who can help me</h2>
          <Muted className="mb-5 text-sm">
            Invite someone you trust who has their own Kavach passkey.
          </Muted>
          <form onSubmit={invite} className="flex items-end gap-3">
            <div className="flex-1">
              <Field
                label="Their Kavach username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <Button type="submit" loading={busy === "invite"}>
              Invite
            </Button>
          </form>
          <ul className="mt-5 divide-y divide-line">
            {data?.my_helpers.map((h) => (
              <li key={h.id} className="flex items-center justify-between py-3">
                <span>
                  {h.display_name} <span className="text-slate">@{h.username}</span>{" "}
                  <Badge tone={h.status === "active" ? "teal" : "amber"}>{h.status}</Badge>
                </span>
                <Button
                  variant="ghost"
                  className="px-3 py-1.5 text-sm text-danger"
                  loading={busy === h.id}
                  onClick={() =>
                    run(
                      h.id,
                      () => api(`/api/helpers/${h.id}`, { method: "DELETE" }),
                      "Helper removed.",
                    )
                  }
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <h2 className="mb-1 text-lg font-bold">People I help</h2>
          <Muted className="mb-5 text-sm">
            You&apos;ll see their sign-in requests on your dashboard.
          </Muted>
          {data?.invitations.map((h) => (
            <div
              key={h.id}
              className="mb-3 flex items-center justify-between rounded-xl bg-mist px-4 py-3"
            >
              <span>
                <b>{h.display_name}</b> invited you to be a helper
              </span>
              <Button
                variant="teal"
                className="px-3 py-2 text-sm"
                loading={busy === h.id}
                onClick={() =>
                  run(
                    h.id,
                    () => api(`/api/helpers/${h.id}/accept`, { method: "POST" }),
                    `You are now a helper for ${h.display_name}.`,
                  )
                }
              >
                Accept
              </Button>
            </div>
          ))}
          <ul className="divide-y divide-line">
            {data?.helping.map((h) => (
              <li key={h.id} className="flex items-center justify-between py-3">
                <span>
                  {h.display_name} <span className="text-slate">@{h.username}</span>
                </span>
                <Button
                  variant="ghost"
                  className="px-3 py-1.5 text-sm text-danger"
                  loading={busy === h.id}
                  onClick={() =>
                    run(
                      h.id,
                      () => api(`/api/helpers/${h.id}`, { method: "DELETE" }),
                      "Stopped helping.",
                    )
                  }
                >
                  Stop helping
                </Button>
              </li>
            ))}
          </ul>
          {data && data.helping.length === 0 && data.invitations.length === 0 && (
            <Muted className="text-sm">Nobody yet.</Muted>
          )}
        </Card>
      </div>

      <p className="mt-6 text-sm">
        <Link href="/dashboard" className="font-semibold text-teal hover:underline">
          ← Back to dashboard
        </Link>
      </p>
    </Shell>
  );
}
