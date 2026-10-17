"""Kavach API — FastAPI application entry point.

Run (from the backend folder, with the venv active):
    uvicorn app.main:app --reload --no-proxy-headers --host 127.0.0.1 --port 8000
The browser never talks to this port directly: the Next.js app on http://localhost:3000
proxies /api/*, /authorize, /token, /userinfo, /logout and /.well-known/* here.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .api import account, alerts, assisted, audit, helpers, oidc, recovery, webauthn
from .db import Base, SessionLocal, engine
from .keys import get_key
from .seed import seed_clients
from .services.assisted_service import AssistError
from .services.oidc_service import OIDCError
from .services.recovery_service import RecoveryError
from .services.webauthn_service import WebAuthnError


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)   # creates new tables (e.g. alerts); never alters old ones
    with engine.begin() as conn:            # columns added after launch, for existing databases
        conn.execute(text("ALTER TABLE passkeys ADD COLUMN IF NOT EXISTS aaguid VARCHAR(36)"))
    get_key()
    with SessionLocal() as db:
        seed_clients(db)
    yield


app = FastAPI(title="Kavach API", version="1.0.0", lifespan=lifespan)


# Domain errors -> clean JSON {"detail": "..."} for the frontend
@app.exception_handler(WebAuthnError)
async def _webauthn_error(_: Request, exc: WebAuthnError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(AssistError)
async def _assist_error(_: Request, exc: AssistError):
    return JSONResponse({"detail": str(exc)}, status_code=exc.status)


@app.exception_handler(RecoveryError)
async def _recovery_error(_: Request, exc: RecoveryError):
    return JSONResponse({"detail": str(exc)}, status_code=exc.status)


@app.exception_handler(OIDCError)
async def _oidc_error(_: Request, exc: OIDCError):
    return JSONResponse({"detail": exc.description, "error": exc.error}, status_code=exc.status)


@app.get("/api/health")
def health():
    with SessionLocal() as db:
        db.execute(text("select 1"))
    return {"ok": True, "database": "connected"}


for module in (webauthn, account, oidc, helpers, assisted, recovery, audit, alerts):
    app.include_router(module.router)
