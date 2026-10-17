// A minimal, standards-only OpenID Connect client (Authorization Code + PKCE).
// This is exactly what any website does to "Sign in with Kavach" — no Kavach-specific code:
// discovery -> redirect to /authorize -> exchange code at /token -> verify the RS256 ID token via JWKS.
import { createRemoteJWKSet, jwtVerify } from "jose";

export const config = {
  issuer: process.env.KAVACH_ISSUER ?? "http://localhost:3000",
  clientId: process.env.KAVACH_CLIENT_ID ?? "college-portal",
  clientSecret: process.env.KAVACH_CLIENT_SECRET ?? "",
  redirectUri: process.env.REDIRECT_URI ?? "http://127.0.0.1:3001/api/auth/callback",
  appUrl: process.env.APP_URL ?? "http://127.0.0.1:3001",
};

let discoveryCache = null;
let jwks = null;

export async function discovery() {
  if (discoveryCache) return discoveryCache;
  const res = await fetch(`${config.issuer}/.well-known/openid-configuration`, {
    cache: "no-store",
  });
  if (!res.ok)
    throw new Error(
      `Kavach discovery failed (${res.status}). Is Kavach running on ${config.issuer}?`,
    );
  discoveryCache = await res.json();
  return discoveryCache;
}

function b64url(bytes) {
  return Buffer.from(bytes).toString("base64url");
}

export function randomString(n = 32) {
  return b64url(crypto.getRandomValues(new Uint8Array(n)));
}

export async function pkceChallenge(verifier) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return b64url(new Uint8Array(digest));
}

export async function authorizeUrl(state, nonce, codeChallenge) {
  const d = await discovery();
  const url = new URL(d.authorization_endpoint);
  url.search = new URLSearchParams({
    response_type: "code",
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    scope: "openid profile",
    state,
    nonce,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  }).toString();
  return url.toString();
}

export async function exchangeCode(code, codeVerifier, expectedNonce) {
  const d = await discovery();
  const basic = Buffer.from(
    `${encodeURIComponent(config.clientId)}:${encodeURIComponent(config.clientSecret)}`,
  ).toString("base64");
  const res = await fetch(d.token_endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Basic ${basic}`,
    },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: config.redirectUri,
      code_verifier: codeVerifier,
    }),
    cache: "no-store",
  });
  const body = await res.json();
  if (!res.ok)
    throw new Error(`Token exchange failed: ${body.error_description ?? body.error ?? res.status}`);

  jwks ??= createRemoteJWKSet(new URL(d.jwks_uri));
  const { payload } = await jwtVerify(body.id_token, jwks, {
    issuer: d.issuer,
    audience: config.clientId,
    algorithms: ["RS256"],
  });
  if (payload.nonce !== expectedNonce) throw new Error("ID token nonce mismatch");
  return payload;
}
