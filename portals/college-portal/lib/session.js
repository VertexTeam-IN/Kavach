// The portal's OWN session (separate from Kavach's). Stored as a signed JWT in an HttpOnly cookie.
import { jwtVerify, SignJWT } from "jose";
import { cookies } from "next/headers";

export const SESSION_COOKIE = "college_sid";
export const FLOW_COOKIE = "college_oidc";

const secret = new TextEncoder().encode(
  process.env.SESSION_SECRET ?? "dev-secret-change-me-dev-secret-change-me",
);

export async function createSessionToken(s, minutes) {
  return new SignJWT({ ...s })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${minutes}m`)
    .sign(secret);
}

export async function getSession() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, secret);
    return payload;
  } catch {
    return null;
  }
}
