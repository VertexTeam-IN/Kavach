// Everything the browser needs from the FastAPI backend is proxied through this app,
// so the browser only ever talks to ONE origin: http://localhost:3000.
// That keeps WebAuthn origin checks, cookies and the OIDC issuer URL consistent.
const API = process.env.KAVACH_API ?? "http://127.0.0.1:8000";

// Browser-side protections on every response. Kept deliberately narrow so nothing breaks:
// no script-src/style-src (Next.js dev + three.js need inline/eval) and no form-action
// (the consent flow redirects to the websites).
const SECURITY_HEADERS = [
  // Clickjacking: no site may put Kavach's sign-in/consent pages in a frame.
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // WebAuthn (publickey-credentials-*) is intentionally left allowed.
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API}/api/:path*` },
      { source: "/authorize", destination: `${API}/authorize` },
      { source: "/token", destination: `${API}/token` },
      { source: "/userinfo", destination: `${API}/userinfo` },
      { source: "/logout", destination: `${API}/logout` },
      { source: "/.well-known/:path*", destination: `${API}/.well-known/:path*` },
    ];
  },
};

export default nextConfig;
