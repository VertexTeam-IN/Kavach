# 5-minute demo script

**Before:** `python -m app.reset_db`, delete old localhost passkeys (Settings → Accounts → Passkeys),
`start-all.bat`. Prepare: Chrome profile A (owner "Dadi"), Chrome profile B (helper "Piyush"), one incognito window.
Pre-register Dadi and Piyush and link them as helper/owner to save time — or do it live if time allows.

| Time | Do | Say |
|---|---|---|
| 0:00 | Slide: problem | "Passwords get phished, reused and leaked. Many people can't manage them — or passkeys — at all." |
| 0:40 | Profile B: register a fresh user → Windows Hello → recovery code | "No password field. Windows created a key pair; the private key never leaves this laptop. Kavach stored only the public key." |
| 1:10 | Sign out → Sign in with passkey | "Kavach sent a random challenge; the laptop signed it after my fingerprint. One touch." |
| 1:30 | College Portal → Continue with Kavach → Allow → dashboard | "The website never sees the passkey — it gets a signed ID token: `acr = passkey`." |
| 2:10 | Citizen Portal (Flask) → Continue with Kavach | "A different stack, off-the-shelf library, zero Kavach code — just issuer, ID and secret." |
| 2:50 | Incognito: College Portal → Get help → Dadi → simulated SMS → code → number 47 | "Dadi has no passkey. She proves her phone, then reads a number to her grandson." |
| 3:20 | Profile B: dashboard → Review → pick 47 → Approve (Windows Hello) | "Piyush approves with *his own* passkey. He never gets her account." |
| 3:40 | Incognito lands on College Portal with amber **view-only** banner | "The website knows it was assisted, so it allows viewing but no changes." |
| 3:50 | Terminal: `python -m pytest -v` | "Replayed signatures, look-alike sites, reused codes, wrong PKCE, wrong number, expired approvals — all rejected." |
| 4:30 | Kavach dashboard → Recent security activity | "Every sign-in and approval is audited. Click. Touch. You're in." |

**If something breaks:** play the backup video; keep talking over the slides.
