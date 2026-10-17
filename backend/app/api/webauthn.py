"""Passkey endpoints: register, login, add backup passkey."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, full_login
from ..schemas import CredentialBody, RegisterStart
from ..security import client_ip, rate_limit
from ..services import audit_service, oidc_service, recovery_service, webauthn_service
from ..services.session_service import create_session

router = APIRouter(prefix="/api/webauthn", tags=["passkeys"])


def _json(body: str) -> Response:
    return Response(content=body, media_type="application/json")


def _after_login(db: Session, req: str | None, sess) -> str:
    """Where to go next. Called AFTER the login is committed, so an expired website
    request never undoes a successful registration/login."""
    if not req:
        return "/dashboard"
    try:
        auth_req = oidc_service.load_auth_request(db, req)
        url = oidc_service.next_step(db, auth_req, sess)
        db.commit()
        return url
    except oidc_service.OIDCError:
        db.rollback()
        return "/dashboard"


# ---------------------------------------------------------------- registration

@router.post("/register/options")
def register_options(body: RegisterStart, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "register", limit=10, window_sec=60)
    return _json(webauthn_service.register_options(db, body.username, body.display_name, body.phone))


@router.post("/register/verify")
def register_verify(body: CredentialBody, request: Request, response: Response, db: Session = Depends(get_db)):
    user, passkey = webauthn_service.register_verify(db, body.credential, label=body.label or "This device")
    recovery_code = recovery_service.issue_code(db, user)
    sess = create_session(db, request, response, user)
    audit_service.log(db, "user_registered", actor_id=user.id, target_id=user.id, ip=client_ip(request))
    audit_service.log(db, "passkey_registered", actor_id=user.id, target_id=passkey.id, ip=client_ip(request))
    db.commit()
    next_url = _after_login(db, body.req, sess)
    return {
        "ok": True,
        "user": {"username": user.username, "display_name": user.display_name},
        "recovery_code": recovery_code,  # shown ONCE; only its hash is stored
        "next": next_url,
    }


# ---------------------------------------------------------------- login

@router.post("/login/options")
def login_options(request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "login", limit=20, window_sec=60)
    return _json(webauthn_service.login_options(db))


@router.post("/login/verify")
def login_verify(body: CredentialBody, request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        user, passkey = webauthn_service.login_verify(db, body.credential)
    except webauthn_service.WebAuthnError:
        audit_service.log(db, "login_failed", ip=client_ip(request), commit=True)
        raise
    sess = create_session(db, request, response, user)
    audit_service.log(db, "login_success", actor_id=user.id, target_id=passkey.id, ip=client_ip(request))
    db.commit()
    next_url = _after_login(db, body.req, sess)
    return {"ok": True, "user": {"username": user.username, "display_name": user.display_name}, "next": next_url}


# ---------------------------------------------------------------- backup passkey

@router.post("/add/options")
def add_options(ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    return _json(webauthn_service.add_options(db, ctx.user))


@router.post("/add/verify")
def add_verify(body: CredentialBody, request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    passkey, _ = webauthn_service.add_verify(db, ctx.user, body.credential, label=body.label or "Backup passkey")
    audit_service.log(db, "passkey_added", actor_id=ctx.user.id, target_id=passkey.id, ip=client_ip(request))
    db.commit()
    return {"ok": True, "id": str(passkey.id)}
