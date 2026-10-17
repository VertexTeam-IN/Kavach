"""Test setup: separate test database, fresh tables per test, helpers for common flows.

Create the test database once (psql as postgres):
    CREATE DATABASE kavach_test OWNER kavach;
Run:
    python -m pytest -v
"""
import base64
import hashlib
import os
import re
import secrets
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://kavach:kavach@127.0.0.1:5432/kavach_test")
os.environ.setdefault("KEY_PATH", "keys/test_signing_key.pem")
os.environ["DEMO_MODE"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.security import reset_rate_limits  # noqa: E402
from app.seed import seed_clients  # noqa: E402

from .soft_authenticator import SoftAuthenticator  # noqa: E402

COLLEGE = {"client_id": "college-portal", "secret": "college-portal-dev-secret",
           "redirect_uri": "http://127.0.0.1:3001/api/auth/callback"}
CITIZEN = {"client_id": "citizen-portal", "secret": "citizen-portal-dev-secret",
           "redirect_uri": "http://127.0.0.1:5000/callback"}


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _clean():
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    with SessionLocal() as db:
        seed_clients(db)
    reset_rate_limits()
    yield


@pytest.fixture
def new_client():
    clients = []

    def make() -> TestClient:
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        return c
    yield make
    for c in clients:
        c.__exit__(None, None, None)


# ---------------------------------------------------------------- flow helpers

def register(client: TestClient, auth: SoftAuthenticator, username: str, phone: str = "9876543210",
             req: str | None = None) -> dict:
    opts = client.post("/api/webauthn/register/options",
                       json={"username": username, "display_name": username.title(), "phone": phone})
    assert opts.status_code == 200, opts.text
    cred = auth.create(opts.json())
    r = client.post("/api/webauthn/register/verify", json={"credential": cred, "req": req})
    assert r.status_code == 200, r.text
    return r.json()


def login(client: TestClient, auth: SoftAuthenticator, req: str | None = None):
    opts = client.post("/api/webauthn/login/options").json()
    return client.post("/api/webauthn/login/verify", json={"credential": auth.get(opts), "req": req})


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def authorize(client: TestClient, site: dict, challenge: str, **extra) -> str:
    params = {"response_type": "code", "client_id": site["client_id"], "redirect_uri": site["redirect_uri"],
              "scope": "openid profile", "state": "st-123", "nonce": "n-456",
              "code_challenge": challenge, "code_challenge_method": "S256", **extra}
    r = client.get("/authorize", params=params, follow_redirects=False)
    assert r.status_code == 302, r.text
    return r.headers["location"]


def query(url: str) -> dict:
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def exchange(client: TestClient, site: dict, code: str, verifier: str):
    return client.post("/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": site["redirect_uri"],
        "client_id": site["client_id"], "client_secret": site["secret"], "code_verifier": verifier,
    })


def latest_otp(client: TestClient, phone: str) -> str:
    msgs = client.get(f"/api/mock-phone/{phone}").json()
    return re.search(r"\b(\d{6})\b", msgs[0]["message"]).group(1)
