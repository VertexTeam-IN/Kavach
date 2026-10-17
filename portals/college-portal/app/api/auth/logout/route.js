import { NextResponse } from "next/server";

import { config, discovery } from "@/lib/oidc";
import { SESSION_COOKIE } from "@/lib/session";

// Clear the portal session, then end the Kavach session too (RP-initiated logout).
export async function GET() {
  let target = new URL("/", config.appUrl).toString();
  try {
    const d = await discovery();
    if (d.end_session_endpoint) {
      const url = new URL(d.end_session_endpoint);
      url.search = new URLSearchParams({
        client_id: config.clientId,
        post_logout_redirect_uri: `${config.appUrl}/`,
      }).toString();
      target = url.toString();
    }
  } catch {
    // Kavach unreachable: still sign out locally
  }
  const res = NextResponse.redirect(target);
  res.cookies.delete(SESSION_COOKIE);
  return res;
}
