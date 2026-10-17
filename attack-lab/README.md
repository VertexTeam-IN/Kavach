# Kavach Attack Lab (demo only)

A dashboard where each button launches one attack against your RUNNING Kavach and shows the
real response. It is a visual version of `backend/tests/test_security.py`.

It changes nothing in Kavach. It only sends HTTP to http://127.0.0.1:8000, the same front door
a browser uses, reusing the backend's virtual environment (FastAPI, httpx, cryptography, cbor2
are already installed there).

## Run

1. `start-all.bat` starts Kavach **and** the lab server (a 5th window, "Attack Lab :4000").
2. Open **http://localhost:3000/lab** — the lab page inside the Kavach app.

(Manual lab server: `cd backend` → `.venv\Scripts\activate` → `cd ..\attack-lab` →
`uvicorn lab:app --host 127.0.0.1 --port 4000`)

### How the pieces fit

```
localhost:3000/lab        frontend/app/lab/page.jsx + components/attack-lab.jsx  (the page)
localhost:3000/lab-api/*  frontend/app/lab-api/[...path]/route.js  (proxy, forwards no cookies)
127.0.0.1:4000/api/*      attack-lab/lab.py  (runs the attacks)  ──►  127.0.0.1:8000 (real Kavach)
```

- The page only exists when `KAVACH_ENABLE_LAB=1` is set in `frontend/.env.local`.
  Without it, `/lab` and `/lab-api/*` return 404. Restart the Kavach UI after changing it.
- The old standalone page still works at http://127.0.0.1:4000 as a fallback.

## How to use in the demo

- Each card = one attack. Click **Run attack** → the steps play back one by one (who acts,
  which request, what Kavach answered), then the verdict. Click **Do it legitimately** to
  show the same flow succeeding when nothing is tampered with. **Run all attacks** walks
  through every card; pick *Slow* speed when presenting.
- The page creates three demo users on first load (victim / helper / attacker) with
  software passkeys, so the attacks need no Windows Hello.

## Honest notes

- **Browser-enforced phishing proof:** for the strongest origin-binding demo, open
  `http://127.0.0.1:3000/login` (a different hostname) and click "Sign in with passkey" —
  the browser itself refuses the passkey. The console's look-alike card is a *simulated*
  origin mismatch.
- **Rate limits:** assisted-start (5/min) and recovery-start are capped per minute, per IP.
  The lab and the real Kavach UI both reach the backend from 127.0.0.1, so they **share**
  that budget: "Run all" uses all 5 assisted starts, so wait a minute before demoing real
  assisted sign-in at /assist. Cards that can't start show RATE LIMITED.
- **Demo only:** never expose this on a real deployment. It exists to visualize blocked
  attacks, not to prove the whole system is secure.
- Lab users accumulate in the DB across restarts; `python -m app.reset_db` clears them.
