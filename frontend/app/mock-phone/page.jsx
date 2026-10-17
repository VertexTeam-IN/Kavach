"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { api } from "@/lib/api";

function PhoneInner() {
  const phone = useSearchParams().get("phone") ?? "";
  const [msgs, setMsgs] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!phone) return;
    const load = () =>
      api(`/api/mock-phone/${encodeURIComponent(phone)}`)
        .then((m) => {
          setMsgs(m);
          setErr(null);
        })
        .catch((e) => setErr(String(e.message ?? e)));
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [phone]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate p-4">
      <div className="w-[340px] rounded-[2.5rem] border-[10px] border-ink bg-white shadow-2xl">
        <div className="flex items-center justify-between rounded-t-[1.8rem] bg-ink px-5 pb-3 pt-2 text-xs text-white">
          <span>Messages</span>
          <span className="rounded bg-amber px-1.5 py-0.5 font-bold text-ink">SIMULATED SMS</span>
        </div>
        <div className="px-4 pb-2 pt-3 text-center text-xs text-slate">
          Demo phone · {phone || "no number"}
          <br />
          (stands in for a real SMS gateway)
        </div>
        <div className="h-[520px] space-y-3 overflow-y-auto px-4 pb-6">
          {err && <p className="text-center text-xs text-danger">{err}</p>}
          {msgs.length === 0 && !err && (
            <p className="pt-10 text-center text-sm text-slate">No messages yet</p>
          )}
          {msgs.map((m, i) => (
            <div
              key={i}
              className={`max-w-[85%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm ${i === 0 ? "bg-teal-soft" : "bg-mist"}`}
            >
              <p className="text-ink">
                {m.message.split(/(\d{6})/).map((part, j) =>
                  /^\d{6}$/.test(part) ? (
                    <b key={j} className="font-mono text-lg">
                      {part}
                    </b>
                  ) : (
                    <span key={j}>{part}</span>
                  ),
                )}
              </p>
              <p className="mt-1 text-[10px] text-slate">{new Date(m.at).toLocaleTimeString()}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function MockPhonePage() {
  return (
    <Suspense>
      <PhoneInner />
    </Suspense>
  );
}
