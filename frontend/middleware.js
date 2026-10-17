import { NextResponse } from "next/server";

// Browsers must not choose their own IP address. Requests proxied to the backend (see the
// rewrites in next.config.mjs) arrive there from 127.0.0.1, and a client-supplied
// X-Forwarded-For would otherwise be believed — giving an attacker a fresh rate-limit budget
// (SMS codes, recovery attempts) on every request. So we drop those headers here.
//
// Behind your own reverse proxy (nginx/Caddy) that OVERWRITES X-Forwarded-For with the real
// client IP, set KAVACH_BEHIND_PROXY=1 so that value is kept. See docs/firewall.md.
const CLIENT_IP_HEADERS = ["x-forwarded-for", "x-real-ip", "forwarded"];

export function middleware(request) {
  if (process.env.KAVACH_BEHIND_PROXY === "1") return NextResponse.next();
  const headers = new Headers(request.headers);
  for (const h of CLIENT_IP_HEADERS) headers.delete(h);
  return NextResponse.next({ request: { headers } });
}

export const config = {
  matcher: ["/api/:path*", "/authorize", "/token", "/userinfo", "/logout", "/.well-known/:path*"],
};
