"""Thin helpers to talk to a RUNNING Kavach, exactly as a browser/website would.

Everything goes to the real endpoints on http://127.0.0.1:8000 (the backend that the
Next.js app on :3000 proxies to). The WebAuthn *origin* that matters is the string inside
clientDataJSON, which the software authenticator sets to http://localhost:3000 — so these
requests pass the same origin/RP-ID/challenge/signature checks as real traffic.

No Kavach code is imported or modified. This module only sends HTTP.
"""
import base64
import hashlib
import os
import re
import secrets
from urllib.parse import parse_qs, urlsplit

import httpx

API = os.environ.get("KAVACH_API", "http://127.0.0.1:8000")
ORIGIN = "http://localhost:3000"          # must match backend RP ORIGIN
RP_ID = "localhost"

COLLEGE = {
    "client_id": "college-portal",
    "secret": "college-portal-dev-secret",
    "redirect_uri": "http://127.0.0.1:3001/api/auth/callback",
}
CITIZEN = {
    "client_id": "citizen-portal",
    "secret": "citizen-portal-dev-secret",
    "redirect_uri": "http://127.0.0.1:5000/callback",
}


class KavachDown(Exception):
    """Raised when the backend can't be reached."""


def client() -> httpx.Client:
    return httpx.Client(base_url=API, timeout=15.0)


def health() -> bool:
    try:
        with client() as c:
            return c.get("/api/health").status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------- PKCE / parsing

def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def query(url: str) -> dict:
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


# ---------------------------------------------------------------- passkey flows

def register(c: httpx.Client, auth, username: str, display_name: str, phone: str):
    opts = c.post("/api/webauthn/register/options",
                  json={"username": username, "display_name": display_name, "phone": phone})
    opts.raise_for_status()
    cred = auth.create(opts.json())
    r = c.post("/api/webauthn/register/verify", json={"credential": cred})
    r.raise_for_status()
    return r.json()


def login_options(c: httpx.Client) -> dict:
    return c.post("/api/webauthn/login/options").json()


def login(c: httpx.Client, auth, req: str | None = None) -> httpx.Response:
    opts = login_options(c)
    return c.post("/api/webauthn/login/verify", json={"credential": auth.get(opts), "req": req})


def logged_in_client(auth) -> httpx.Client:
    c = client()
    r = login(c, auth)
    r.raise_for_status()
    return c


# ---------------------------------------------------------------- OIDC

def authorize(c: httpx.Client, site: dict, challenge: str, **extra) -> httpx.Response:
    params = {
        "response_type": "code", "client_id": site["client_id"], "redirect_uri": site["redirect_uri"],
        "scope": "openid profile", "state": "demo-state", "nonce": "demo-nonce",
        "code_challenge": challenge, "code_challenge_method": "S256", **extra,
    }
    return c.get("/authorize", params=params, follow_redirects=False)


def exchange(c: httpx.Client, site: dict, code: str, verifier: str, secret: str | None = None) -> httpx.Response:
    return c.post("/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": site["redirect_uri"],
        "client_id": site["client_id"], "client_secret": secret if secret is not None else site["secret"],
        "code_verifier": verifier,
    })


def get_authorization_code(auth, site: dict, verifier: str, challenge: str) -> tuple[httpx.Client, str]:
    """Full legitimate flow up to a fresh authorization code: returns (client, code).

    Mirrors the browser: /authorize -> sign in with passkey -> (consent) -> redirect with code.
    """
    c = client()
    loc = authorize(c, site, challenge, prompt="login").headers["location"]
    req = query(loc)["req"]
    nxt = login(c, auth, req=req).json().get("next", "")
    if nxt.startswith("/consent"):
        redirect = c.post("/api/oidc/consent", json={"req": req, "allow": True}).json()["redirect"]
    elif nxt.startswith("http"):
        redirect = nxt
    else:
        redirect = c.post("/api/oidc/consent", json={"req": req, "allow": True}).json()["redirect"]
    return c, query(redirect)["code"]


# ---------------------------------------------------------------- assisted / mock SMS

def mock_messages(phone: str) -> list[dict]:
    with client() as c:
        r = c.get(f"/api/mock-phone/{phone}")
        return r.json() if r.status_code == 200 else []


def latest_otp(phone: str) -> str | None:
    msgs = mock_messages(phone)
    if not msgs:
        return None
    m = re.search(r"\b(\d{6})\b", msgs[0]["message"])
    return m.group(1) if m else None
