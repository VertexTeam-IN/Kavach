# Threat model (one page)

| Threat | Mitigation in Kavach |
|---|---|
| Phishing / look-alike site | WebAuthn binds signatures to origin + RP ID; backend verifies both. Nothing typed to steal. |
| Server database breach | Only public keys and hashes stored (SHA-256 for tokens/codes/OTPs, argon2 for client secrets and recovery codes). No passwords exist. |
| Replay of a captured login | Fresh 32-byte challenge per ceremony, 2-minute expiry, consumed atomically (`UPDATE … WHERE consumed_at IS NULL RETURNING`). |
| Stolen laptop | Private key is in the TPM and needs the owner's Windows Hello (fingerprint/face/PIN); `userVerification=required` is enforced server-side. User can revoke the passkey and sessions. |
| Stolen authorization code | 60-second single-use codes bound to client + redirect URI + **PKCE**; client authentication with argon2-hashed secrets. |
| Open redirect / token theft | Exact-match redirect URIs; invalid client/redirect shows an error page instead of redirecting. |
| Forged ID token | RS256 signatures; websites verify with JWKS, check `iss`, `aud`, `exp`, `nonce`. |
| Assisted access abuse — attacker starts a request | Owner must enter an OTP sent to their registered phone (max 5 tries). |
| Assisted access — helper approves blindly / push fatigue | **Number matching**: helper must pick the number the owner reads out; 2 wrong picks cancel the request. |
| Assisted access — approval replay or reuse | Approval is bound to one request, expires in 3 minutes, consumed once atomically. |
| Assisted access — helper takeover | Helper uses *their own* passkey; never receives owner credentials. Assisted sessions are 15 minutes, flagged `acr=assisted`, and blocked from managing passkeys, helpers, sessions or recovery. Websites can refuse assisted logins (`allow_assisted=false` or `acr_values`). |
| SIM swap / OTP interception | OTP alone never grants access: assisted login also needs a helper's passkey + number match; recovery also needs the offline recovery code. |
| Lost device | Backup passkey (phone) or recovery code + OTP → new passkey; all old passkeys and sessions revoked. |
| Brute force | Per-IP rate limits on register, login, OTP, recovery and token endpoints. |
| Session theft (XSS) | HttpOnly, SameSite=Lax cookies; session rotated after login; tokens never in localStorage. |

**Known limits (state honestly):** SMS is simulated in the demo; anyone enrolled in Windows Hello on the
same Windows account can use its passkeys; no admin-verified recovery yet; rate limits are in-memory
(single server).
