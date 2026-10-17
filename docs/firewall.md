# Firewall & network hardening

What is already applied in this project, and what to add when Kavach goes beyond a laptop demo.

## Applied in the code

| Protection | Where | What it stops |
|---|---|---|
| **Strip client IP headers** | `frontend/middleware.js` | Browsers can no longer send `X-Forwarded-For` / `X-Real-IP` / `Forwarded` to the backend. Without this, a fake IP gets a fresh rate-limit budget on every request (unlimited SMS codes, recovery-code guessing). Set `KAVACH_BEHIND_PROXY=1` only behind a proxy that overwrites the header. |
| **Uvicorn proxy headers off** | `start-all.bat`, README → `uvicorn … --no-proxy-headers` | Uvicorn trusts `X-Forwarded-For` from 127.0.0.1 **by default** and rewrites the client address before Kavach sees it. Turned off so Kavach's own rule below decides. |
| **Trusted-proxy client IP** | `backend/app/security.py` → `client_ip()`, setting `TRUSTED_PROXIES` | `X-Forwarded-For` is only believed from your own proxies, reading right-to-left. Default: trust no one. |
| **Browser security headers** | `frontend/next.config.mjs` → `headers()` | Clickjacking of the sign-in / consent pages (`frame-ancestors 'none'`, `X-Frame-Options`), MIME sniffing, `<base>` / plugin injection, and unneeded browser features. WebAuthn is left allowed. |
| **Loopback-only services** | `start-all.bat`, `.env` | API (8000), portals (3001/5000), lab (4000) and PostgreSQL listen on `127.0.0.1`. |
| **Lab gate** | `frontend/.env.local` → `KAVACH_ENABLE_LAB` | `/lab` and `/lab-api/*` are 404 unless explicitly turned on. |

Proved by `backend/tests/test_security.py` (`test_spoofed_forwarded_for_does_not_bypass_rate_limit`,
`test_forwarded_for_is_used_from_a_trusted_proxy`) and the Attack Lab card **Fake IP to dodge rate limits**.

## Laptop demo (Windows)

`next dev` (the Kavach UI on :3000) listens on **all** network interfaces, so on shared Wi-Fi anyone
could open `http://<your-ip>:3000` — including `/lab`. Block that with Windows Defender Firewall
(Administrator PowerShell, run once):

```powershell
powershell -ExecutionPolicy Bypass -File firewall\windows-firewall-on.ps1
```

It blocks inbound connections from **other machines** to 3000, 3001, 3002, 4000, 5000, 8000 and 5432.
Traffic on the laptop itself is never filtered, so Kavach works exactly as before.
Undo with `firewall\windows-firewall-off.ps1`.

## Real deployment

Only one port is public. Everything else is private.

```
Internet ─► [Cloudflare / WAF] ─► [Caddy or nginx :443] ─► Next.js 127.0.0.1:3000 ─► FastAPI 127.0.0.1:8000 ─► PostgreSQL
```

**1. Network firewall** (ufw / nftables / cloud security groups): allow 80 + 443 from anywhere,
22 from your own IP only, deny everything else.

```bash
ufw default deny incoming && ufw allow 80,443/tcp && ufw allow from <your-ip> to any port 22 && ufw enable
```

**2. Reverse proxy** — TLS (passkeys require HTTPS on a real domain) and the *real* client IP.

Caddy (sets `X-Forwarded-For` itself and ignores what the client sent):

```
login.example.com {
    reverse_proxy 127.0.0.1:3000
}
```

nginx (overwrite, never append the client's header):

```nginx
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Then set `KAVACH_BEHIND_PROXY=1` for the Next.js app (so it keeps the proxy's header) and
`TRUSTED_PROXIES=127.0.0.1` in `backend/.env` (the Next.js server, which passes it through). Keep
`--no-proxy-headers` on uvicorn. Do this **only** when port 3000 is not reachable from outside —
otherwise a client could talk to Next.js directly with a fake header.

Also set for HTTPS: `COOKIE_SECURE=true`, `ORIGIN` / `ISSUER` / `RP_ID` to the real domain, and add
`Strict-Transport-Security: max-age=31536000` at the proxy.

**3. WAF** (Cloudflare free tier, or ModSecurity / Coraza + OWASP Core Rule Set). Start in
detection-only mode: WebAuthn requests carry long base64 blobs (`clientDataJSON`,
`attestationObject`, signatures) that generic rules can mistake for attacks. Add exceptions for
`/api/webauthn/*` if real sign-ins get flagged, and allow `/authorize`, `/token`, `/userinfo`,
`/.well-known/*`. Edge rate limits on `/api/assist`, `/api/recovery/*` and `/api/webauthn/*/options`
are a good second layer.

**4. Database**: `listen_addresses = 'localhost'` in `postgresql.conf`; in `pg_hba.conf` allow the
`kavach` user only from the backend's address.

**5. Never deploy the Attack Lab**: leave `KAVACH_ENABLE_LAB` unset and don't run `attack-lab/`.

## Known limits (code, not firewall)

- Rate limits are in memory: they reset on restart and aren't shared between several backend
  processes. Move them to Redis before running more than one backend.
- All browser traffic reaches the backend through Next.js, so without a trusted proxy in front every
  browser user shares the `127.0.0.1` rate-limit budget (fine for a single-laptop demo).
