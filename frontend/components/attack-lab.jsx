"use client";

// Attack Lab (DEMO ONLY) — each card runs a real attack against the running Kavach backend
// through the lab server (attack-lab/lab.py, reached via /lab-api) and plays the result
// back step by step. Served at /lab only when KAVACH_ENABLE_LAB=1.

import { useCallback, useEffect, useRef, useState } from "react";

import { Alert, Badge, Brand, Button, Card, H1, Muted, Shell } from "@/components/ui";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function lab(path, method = "GET") {
  const r = await fetch(`/lab-api/${path}`, { method, cache: "no-store" });
  let data;
  try {
    data = await r.json();
  } catch {
    throw new Error(`Attack Lab answered ${r.status} without JSON.`);
  }
  if (!r.ok && data?.detail) throw new Error(data.detail);
  return data;
}

const SPEEDS = [
  { ms: 1600, label: "Slow (presenting)" },
  { ms: 900, label: "Normal" },
  { ms: 250, label: "Fast" },
];

const WHO_TONE = { victim: "teal", helper: "success", attacker: "danger", website: "violet", kavach: "mist" };

const STATUS_TEXT = {
  200: "OK", 302: "Redirect", 303: "Redirect", 400: "Bad Request", 401: "Unauthorized",
  403: "Forbidden", 404: "Not Found", 429: "Too Many Requests",
};

const OUTCOME = {
  blocked: { tone: "success", label: "BLOCKED", box: "border-emerald-500/30 bg-emerald-950/20 text-emerald-200" },
  allowed: { tone: "teal", label: "ALLOWED", box: "border-blue-500/30 bg-blue-950/30 text-blue-200" },
};
const outcomeOf = (o) =>
  OUTCOME[o] ?? { tone: "danger", label: (o || "check").toUpperCase(), box: "border-red-500/30 bg-red-950/20 text-red-200" };

const STEP_BORDER = { ok: "border-blue-500", blocked: "border-emerald-500", warn: "border-red-500", info: "border-amber-500" };

function Who({ who = "kavach" }) {
  return (
    <Badge tone={WHO_TONE[who] ?? "mist"}>
      <span className="text-[10px] font-bold uppercase tracking-wider">{who}</span>
    </Badge>
  );
}

function StatusCode({ status }) {
  const c = Math.floor(status / 100);
  const tone =
    c === 2 ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
    : c === 3 ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
    : "border-red-500/30 bg-red-500/10 text-red-300";
  return (
    <span className={`rounded-md border px-1.5 ${tone}`}>
      {status} {STATUS_TEXT[status] ?? ""}
    </span>
  );
}

function Step({ step, n, current }) {
  const raw = [];
  if (step.request !== undefined) raw.push(`→ request ${JSON.stringify(step.request, null, 2)}`);
  if (step.body !== undefined) raw.push(JSON.stringify(step.body, null, 2));
  return (
    <li
      className={`kv-rise border-l-2 py-1.5 pl-3 text-[12.5px] text-slate-300 ${STEP_BORDER[step.kind] ?? "border-slate-700"} ${
        current ? "rounded-r-lg bg-blue-600/10" : ""
      }`}
      style={{ animationDuration: "0.35s" }}
    >
      <div className="flex flex-wrap items-center gap-2 font-semibold text-slate-100">
        <span className="min-w-4 font-mono font-medium text-slate-500">{n}.</span>
        <Who who={step.who} />
        <span>{step.title}</span>
      </div>
      {step.call && (
        <div className="mt-1.5 break-all font-mono text-[11px] text-slate-400">
          {step.call} → <StatusCode status={step.status} />
          {step.kind === "blocked" && <span className="ml-2 font-sans font-semibold text-emerald-300">✓ defence held</span>}
        </div>
      )}
      {step.note && <div className="mt-1 leading-relaxed text-slate-400">{step.note}</div>}
      {raw.length > 0 && (
        <details className="mt-1.5">
          <summary className="cursor-pointer font-mono text-[11px] text-slate-500 hover:text-slate-400">
            show server response
          </summary>
          {raw.map((t, i) => (
            <pre
              key={i}
              className="mt-1.5 max-h-44 overflow-auto rounded-lg border border-slate-800 bg-[#0b0f19] p-2.5 font-mono text-[11px] leading-relaxed text-slate-300"
            >
              {t}
            </pre>
          ))}
        </details>
      )}
    </li>
  );
}

function AttackCard({ card, speedRef, register }) {
  const [phase, setPhase] = useState("idle"); // idle | loading | playing | done
  const [res, setRes] = useState(null);
  const [shown, setShown] = useState(0);
  const [legitRun, setLegitRun] = useState(false);
  const playId = useRef(0); // bumping it cancels a playback that is still going
  const el = useRef(null);

  const play = useCallback(
    async (r, instant = false) => {
      const id = ++playId.current;
      const n = r.steps?.length ?? 0;
      setRes(r);
      if (instant) {
        setShown(n);
        setPhase("done");
        return;
      }
      setPhase("playing");
      setShown(0);
      for (let i = 1; i <= n; i++) {
        if (playId.current !== id) return;
        setShown(i);
        await sleep(speedRef.current);
      }
      if (playId.current === id) setPhase("done");
    },
    [speedRef],
  );

  const run = useCallback(
    async (legit = false) => {
      playId.current++;
      setLegitRun(legit);
      setPhase("loading");
      setRes(null);
      setShown(0);
      try {
        await play(await lab(`${legit ? "legit" : "run"}/${card.id}`, "POST"));
      } catch (e) {
        setRes({ outcome: "error", verdict: `Lab error: ${e.message}`, steps: [] });
        setPhase("done");
      }
    },
    [card.id, play],
  );

  useEffect(() => register(card.id, { run, el }), [card.id, run, register]);

  const busy = phase === "loading" || phase === "playing";
  const steps = res?.steps ?? [];
  const live = busy;
  const o = res && outcomeOf(res.outcome);

  return (
    <section
      ref={el}
      className={`kv-rise flex flex-col gap-3 rounded-2xl border bg-[#111827] p-5 shadow-lg shadow-black/25 transition sm:p-6 ${
        live ? "border-blue-500/60 ring-4 ring-blue-600/20" : "border-slate-800 hover:border-slate-700"
      }`}
    >
      <h3 className="font-display text-[17px] font-semibold tracking-tight text-white">{card.title}</h3>
      <p className="text-[13px] leading-relaxed text-slate-400">{card.attacker}</p>
      <p className="rounded-xl border border-slate-800 bg-slate-800/40 px-3 py-2.5 text-[12.5px] leading-relaxed text-slate-300">
        <b className="font-bold text-blue-400">What this means: </b>
        {card.explain}
      </p>
      <div className="text-[11px] leading-relaxed text-slate-500">
        Threat: {card.threat} · Test: <code className="font-mono text-[10.5px] text-slate-400">{card.test}</code>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => run(false)} disabled={busy} loading={phase === "loading" && !legitRun}>
          Run attack
        </Button>
        {card.has_legit && (
          <Button variant="secondary" onClick={() => run(true)} disabled={busy} loading={phase === "loading" && legitRun}>
            Do it legitimately
          </Button>
        )}
      </div>

      {phase === "loading" && (
        <Alert kind="warn">Sending real requests to Kavach… ({legitRun ? "legitimate flow" : "attack"})</Alert>
      )}

      {res && phase !== "loading" && (
        <div className="mt-0.5 flex flex-col gap-2.5 border-t border-slate-800 pt-3">
          <div className="flex items-center justify-between gap-2 font-mono text-[11px] text-slate-400">
            <span>
              {phase === "done"
                ? `Done in ${res.ms ?? "?"} ms · ${steps.length} step${steps.length === 1 ? "" : "s"}`
                : `Step ${shown} of ${steps.length}`}
            </span>
            {steps.length > 0 &&
              (phase === "playing" ? (
                <button
                  onClick={() => play(res, true)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 font-sans text-[11.5px] font-semibold text-slate-300 transition hover:bg-slate-700 hover:text-white"
                >
                  Skip ⏭
                </button>
              ) : (
                <button
                  onClick={() => play(res)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 font-sans text-[11.5px] font-semibold text-slate-300 transition hover:bg-slate-700 hover:text-white"
                >
                  Replay ↺
                </button>
              ))}
          </div>
          <div className="h-[3px] overflow-hidden rounded bg-slate-800">
            <i
              className="block h-full bg-gradient-to-r from-blue-600 to-blue-400 transition-all duration-300"
              style={{ width: `${steps.length ? (shown / steps.length) * 100 : 100}%` }}
            />
          </div>
          <ol className="flex flex-col gap-2">
            {steps.slice(0, shown).map((s, i) => (
              <Step key={i} step={s} n={i + 1} current={phase === "playing" && i === shown - 1} />
            ))}
          </ol>
          {phase === "done" && (
            <div className={`rounded-xl border px-3 py-2.5 text-[12.5px] font-medium leading-relaxed ${o.box}`}>
              <span className="mr-2 align-[1px]">
                <Badge tone={o.tone}>
                  <span className="text-[10.5px] font-bold">{o.label}</span>
                </Badge>
              </span>
              {res.verdict}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function LabHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-800 bg-[#0b0f19]/90 backdrop-blur-md">
      <div className="mx-auto flex h-[54px] max-w-6xl items-center justify-between gap-6 px-5">
        <div className="flex items-center gap-3">
          <Brand />
          <span className="hidden text-slate-600 sm:inline">/</span>
          <span className="hidden font-display text-[15px] font-semibold text-slate-300 sm:inline">Attack Lab</span>
        </div>
        <div className="flex items-center gap-5">
          <a href="http://127.0.0.1:3001" target="_blank" rel="noopener" className="hidden text-[13px] font-medium text-slate-300 transition hover:text-white md:inline">
            College Portal
          </a>
          <a href="http://127.0.0.1:5000" target="_blank" rel="noopener" className="hidden text-[13px] font-medium text-slate-300 transition hover:text-white md:inline">
            Citizen Portal
          </a>
          <Badge tone="amber">DEMO ONLY</Badge>
        </div>
      </div>
    </header>
  );
}

export default function AttackLab() {
  const [cards, setCards] = useState([]);
  const [target, setTarget] = useState("");
  const [scenario, setScenario] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [speed, setSpeed] = useState(900);
  const [runAllAt, setRunAllAt] = useState(null); // null, or index of the card being run
  const speedRef = useRef(speed);
  const runners = useRef({});

  useEffect(() => {
    speedRef.current = speed;
  }, [speed]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const meta = await lab("cards");
        if (!alive) return;
        setCards(meta.cards);
        setTarget(meta.target);
        const st = await lab("scenario");
        if (alive) setScenario(st);
      } catch (e) {
        if (alive) setLoadError(e.message);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const register = useCallback((id, runner) => {
    runners.current[id] = runner;
  }, []);

  async function runAll() {
    for (let i = 0; i < cards.length; i++) {
      setRunAllAt(i);
      const r = runners.current[cards[i].id];
      if (!r) continue;
      r.el.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      await r.run(false);
      await sleep(speedRef.current);
    }
    setRunAllAt(null);
  }

  const groups = [];
  for (const c of cards) {
    let g = groups.find((x) => x.name === c.group);
    if (!g) groups.push((g = { name: c.group, cards: [] }));
    g.cards.push(c);
  }

  return (
    <Shell header={<LabHeader />} mainClassName="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
      <section className="kv-rise pb-2 pt-10">
        <div className="kv-eyebrow">Security checks · live</div>
        <H1 className="mt-3.5 sm:text-[30px]">Try to break Kavach</H1>
        <Muted className="mt-2 max-w-2xl">
          Each card is a real attack, sent as real HTTP to the running Kavach backend. Watch it play out step by
          step: who acts, which request goes out and what Kavach answers. Then click{" "}
          <b className="text-white">Do it legitimately</b> to see the same flow work when nothing is tampered with.
        </Muted>
      </section>

      <div className="mt-5">
        {loadError ? (
          <Alert kind="error">{loadError}</Alert>
        ) : scenario?.error ? (
          <Alert kind="error">{scenario.error}</Alert>
        ) : scenario?.ready ? (
          <Alert kind="success">
            <span className="inline-flex flex-wrap items-center gap-1.5 leading-6">
              Kavach reached. Demo users ready — <Who who="victim" /> <b className="text-white">{scenario.victim}</b>,{" "}
              <Who who="helper" /> <b className="text-white">{scenario.helper}</b>, <Who who="attacker" />{" "}
              <b className="text-white">{scenario.attacker}</b>.
            </span>
          </Alert>
        ) : (
          <Alert kind="info">Checking Kavach and setting up demo users…</Alert>
        )}
      </div>

      <Card className="mt-3.5 !p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-400">
            <span className="inline-flex items-center gap-1.5"><Badge tone="success">BLOCKED</Badge> attack refused</span>
            <span className="inline-flex items-center gap-1.5"><Badge tone="teal">ALLOWED</Badge> legit flow works</span>
            <span className="inline-flex items-center gap-1.5"><Badge tone="danger">CHECK</Badge> look at the steps</span>
            <span className="inline-flex items-center gap-1">
              <Who who="victim" /><Who who="helper" /><Who who="attacker" /><Who who="website" />
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <label className="flex items-center gap-2">
              Speed
              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="rounded-xl border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-white outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              >
                {SPEEDS.map((s) => (
                  <option key={s.ms} value={s.ms}>{s.label}</option>
                ))}
              </select>
            </label>
            <Button onClick={runAll} disabled={runAllAt !== null || !cards.length}>
              {runAllAt !== null ? `Running ${runAllAt + 1} of ${cards.length}…` : "▶ Run all attacks"}
            </Button>
          </div>
        </div>
      </Card>

      {groups.map((g) => (
        <section key={g.name} className="mt-9">
          <div className="kv-eyebrow">{g.name}</div>
          <div className="mt-3.5 grid gap-4 md:grid-cols-2">
            {g.cards.map((c) => (
              <AttackCard key={c.id} card={c} speedRef={speedRef} register={register} />
            ))}
          </div>
        </section>
      ))}

      <p className="mt-12 border-t border-slate-800 pt-5 text-xs leading-relaxed text-slate-500">
        Target: <code className="font-mono text-slate-400">{target}</code> · Browser-enforced phishing proof: open{" "}
        <code className="font-mono text-slate-400">http://127.0.0.1:3000/login</code> on a different hostname — the
        browser itself refuses the passkey. This lab demonstrates defences against the specific listed attacks; it does
        not prove the system is secure overall. Assisted sign-in starts are limited to 5 per minute, shared with the
        real Kavach UI.
      </p>
    </Shell>
  );
}
