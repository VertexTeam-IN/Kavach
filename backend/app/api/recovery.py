"""Account recovery: recovery code + phone OTP -> register a new passkey -> old passkeys revoked."""
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User
from ..schemas import CredentialBody, OtpBody, RecoveryStart
from ..security import client_ip, rate_limit
from ..services import audit_service, oidc_service, recovery_service, webauthn_service
from ..services.recovery_service import RecoveryError
from ..services.session_service import create_session

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


def _after_login(db: Session, req: str | None, sess) -> str:
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


@router.post("/verify")
@router.post("/recover")
def recover(body: RecoveryStart, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, "recovery_recover", limit=5, window_sec=300)
    try:
        user, new_code = recovery_service.recover_with_code(db, body.username.strip().lower(), body.code)
    except RecoveryError:
        audit_service.log(db, "recovery_failed", ip=client_ip(request), commit=True)
        raise
    sess = create_session(db, request, response, user)
    audit_service.log(db, "account_recovered", actor_id=user.id, ip=client_ip(request))
    db.commit()
    next_url = _after_login(db, body.req, sess)
    return {"ok": True, "recovery_code": new_code, "next": next_url}


@router.post("/start")
def start(body: RecoveryStart, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "recovery_start", limit=5, window_sec=300)
    try:
        req, token = recovery_service.start(db, body.username.strip().lower(), body.code)
    except RecoveryError:
        audit_service.log(db, "recovery_failed", ip=client_ip(request), commit=True)
        raise
    user = db.get(User, req.user_id)
    audit_service.log(db, "recovery_started", actor_id=user.id, target_id=req.id, ip=client_ip(request))
    db.commit()
    return {
        "id": str(req.id),
        "token": token,
        "phone_hint": f"••••••{user.phone[-4:]}",
        "demo_phone": user.phone if settings.DEMO_MODE else None,
    }


@router.post("/{recovery_id}/otp")
def verify_otp(recovery_id: uuid.UUID, body: OtpBody, request: Request,
               x_recovery_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    rate_limit(request, "recovery_otp", limit=10, window_sec=60)
    req = recovery_service.load(db, recovery_id, x_recovery_token)
    try:
        recovery_service.verify_otp(db, req, body.otp)
    finally:
        db.commit()
    return {"ok": True}


@router.post("/{recovery_id}/register/options")
def register_options(recovery_id: uuid.UUID, x_recovery_token: str | None = Header(default=None),
                     db: Session = Depends(get_db)):
    req = recovery_service.load(db, recovery_id, x_recovery_token)
    if not req.verified_at:
        raise HTTPException(400, "Verify the SMS code first")
    user = db.get(User, req.user_id)
    return Response(
        content=webauthn_service.add_options(db, user, purpose="recovery", context={"recovery_id": str(req.id)}),
        media_type="application/json",
    )


@router.post("/{recovery_id}/register/verify")
def register_verify(recovery_id: uuid.UUID, body: CredentialBody, request: Request, response: Response,
                    x_recovery_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    req = recovery_service.load(db, recovery_id, x_recovery_token)
    if not req.verified_at:
        raise HTTPException(400, "Verify the SMS code first")
    user = db.get(User, req.user_id)
    passkey, ch = webauthn_service.add_verify(db, user, body.credential, purpose="recovery",
                                              label=body.label or "New device (recovered)")
    if ch.context.get("recovery_id") != str(req.id):
        db.rollback()
        raise HTTPException(400, "Registration does not belong to this recovery")
    new_code = recovery_service.complete(db, req, user, passkey)
    create_session(db, request, response, user)
    audit_service.log(db, "account_recovered", actor_id=user.id, target_id=passkey.id, ip=client_ip(request))
    db.commit()
    return {"ok": True, "recovery_code": new_code, "next": "/dashboard"}
