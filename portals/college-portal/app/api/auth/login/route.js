import { NextResponse } from "next/server";

import { authorizeUrl, pkceChallenge, randomString } from "@/lib/oidc";
import { FLOW_COOKIE } from "@/lib/session";

// Step 1: send the user to Kavach with state, nonce and a PKCE challenge.
export async function GET() {
  const state = randomString(16);
  const nonce = randomString(16);
  const verifier = randomString(48);
  const url = await authorizeUrl(state, nonce, await pkceChallenge(verifier));

  const res = NextResponse.redirect(url);
  res.cookies.set(FLOW_COOKIE, JSON.stringify({ state, nonce, verifier }), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 600,
  });
  return res;
}
