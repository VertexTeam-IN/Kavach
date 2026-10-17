import { NextResponse } from "next/server";

import { config, exchangeCode } from "@/lib/oidc";
import { createSessionToken, FLOW_COOKIE, SESSION_COOKIE } from "@/lib/session";

const ASSISTED = "urn:kavach:acr:assisted";

// Step 2: Kavach redirects back here with ?code&state. Exchange the code server-to-server.
export async function GET(req) {
  const params = req.nextUrl.searchParams;
  const home = new URL("/", config.appUrl);

  if (params.get("error")) {
    home.searchParams.set("error", params.get("error_description") ?? params.get("error"));
    return NextResponse.redirect(home);
  }

  const flowRaw = req.cookies.get(FLOW_COOKIE)?.value;
  const flow = flowRaw ? JSON.parse(flowRaw) : null;
  if (!flow || flow.state !== params.get("state")) {
    home.searchParams.set("error", "Sign-in expired or state mismatch. Please try again.");
    return NextResponse.redirect(home);
  }

  try {
    const claims = await exchangeCode(params.get("code") ?? "", flow.verifier, flow.nonce);
    const assisted = claims.acr === ASSISTED;
    const token = await createSessionToken(
      {
        sub: String(claims.sub),
        name: claims.name ?? "Student",
        username: claims.preferred_username ?? "",
        assisted,
        assistedBy: claims.kavach_assisted_by ?? null,
      },
      assisted ? 15 : 480,
    );
    const res = NextResponse.redirect(new URL("/dashboard", config.appUrl));
    res.cookies.delete(FLOW_COOKIE);
    res.cookies.set(SESSION_COOKIE, token, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: (assisted ? 15 : 480) * 60,
    });
    return res;
  } catch (e) {
    home.searchParams.set("error", e.message);
    return NextResponse.redirect(home);
  }
}
