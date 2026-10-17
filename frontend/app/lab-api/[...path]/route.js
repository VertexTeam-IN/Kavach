// Proxy for the Attack Lab page (/lab) to the lab server (attack-lab/lab.py on :4000).
//
// A route handler rather than a rewrite in next.config.mjs, on purpose:
//  - it forwards NO cookies or headers, so the browser's Kavach session never reaches the lab;
//  - only the lab's own endpoints are reachable;
//  - the KAVACH_ENABLE_LAB gate is checked on every request.
// DEMO ONLY — leave KAVACH_ENABLE_LAB unset anywhere real.

const LAB = process.env.KAVACH_LAB_API ?? "http://127.0.0.1:4000";
const ALLOWED = /^(cards|scenario|(run|legit)\/[a-z_]+)$/;

export const dynamic = "force-dynamic";

async function proxy(request, { params }) {
  if (process.env.KAVACH_ENABLE_LAB !== "1") {
    return new Response("Not found", { status: 404 });
  }
  const path = (await params).path.join("/");
  if (!ALLOWED.test(path)) {
    return new Response("Not found", { status: 404 });
  }
  try {
    const r = await fetch(`${LAB}/api/${path}`, {
      method: request.method,
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { "content-type": r.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json(
      {
        error: "lab_down",
        detail: `The Attack Lab server isn't reachable on ${LAB}. Start it (start-all.bat starts it too) and reload.`,
      },
      { status: 502 },
    );
  }
}

export { proxy as GET, proxy as POST };
