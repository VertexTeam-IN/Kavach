"""Assisted access endpoints (owner side uses the X-Assist-Token header; helper side uses their session)."""
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import Response as RawResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import Ctx, full_login
from ..models import MockSMS, User
from ..schemas import ApproveVerify, AssistStart, OtpBody
from ..security import client_ip, rate_limit
from ..services import assisted_service, audit_service, oidc_service, webauthn_service
from ..services.assisted_service import AssistError
from ..services.session_service import ACR_ASSISTED, create_session

router = APIRouter(prefix="/api", tags=["assisted"])


# ---------------------------------------------------------------- owner side

@router.post("/assist")
def start(body: AssistStart, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "assist_start", limit=5, window_sec=60)
    auth_req = oidc_service.load_auth_request(db, body.req) if body.req else None
    req, token = assisted_service.start(db, body.username.strip().lower(), auth_req)
    audit_service.log(db, "assist_requested", actor_id=req.owner_id, target_id=req.id,
                      client_id=req.client_id, ip=client_ip(request))
    db.commit()
    owner = db.get(User, req.owner_id)
    return {
        "id": str(req.id),
        "token": token,  # keep in the owner's browser only
        "status": req.status,
        "phone_hint": f"••••••{owner.phone[-4:]}",
        "expires_at": req.expires_at.isoformat(),
        "demo_phone": owner.phone if settings.DEMO_MODE else None,
    }


@router.post("/assist/{assist_id}/otp")
def verify_otp(assist_id: uuid.UUID, body: OtpBody, request: Request,
               x_assist_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    rate_limit(request, "assist_otp", limit=10, window_sec=60)
    req = assisted_service.load_for_owner(db, assist_id, x_assist_token)
    try:
        assisted_service.verify_otp(db, req, body.otp)
    except AssistError:
        db.commit()  # keep attempt counter
        raise
    audit_service.log(db, "assist_otp_verified", actor_id=req.owner_id, target_id=req.id, ip=client_ip(request))
    db.commit()
    return assisted_service.public_view(db, req, for_helper=False)


@router.get("/assist/{assist_id}")
def owner_status(assist_id: uuid.UUID, x_assist_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    req = assisted_service.load_for_owner(db, assist_id, x_assist_token)
    db.commit()
    return assisted_service.public_view(db, req, for_helper=False)


@router.post("/assist/{assist_id}/cancel")
def owner_cancel(assist_id: uuid.UUID, x_assist_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    req = assisted_service.load_for_owner(db, assist_id, x_assist_token)
    if req.status not in assisted_service.TERMINAL:
        req.status = "cancelled"
    db.commit()
    return {"ok": True}


@router.post("/assist/{assist_id}/complete")
def owner_complete(assist_id: uuid.UUID, request: Request, response: Response,
                   x_assist_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    """After the helper approved: consume the approval ONCE and sign the owner in (assisted)."""
    req = assisted_service.load_for_owner(db, assist_id, x_assist_token)
    if not assisted_service.consume(db, req):
        db.commit()
        audit_service.log(db, "assist_replay_blocked", actor_id=req.owner_id, target_id=req.id,
                          ip=client_ip(request), commit=True)
        raise HTTPException(400, "This approval is not available — it was already used, expired, or not approved yet.")
    owner = db.get(User, req.owner_id)
    sess = create_session(db, request, response, owner, acr=ACR_ASSISTED, amr=["otp", "helper"],
                          assisted_by_id=req.approved_by_id)
    redirect = "/dashboard"
    if req.auth_request_id:
        auth_req = oidc_service.load_auth_request(db, req.auth_request_id)
        redirect = oidc_service.next_step(db, auth_req, sess)
    audit_service.log(db, "assist_login", actor_id=owner.id, target_id=req.id, client_id=req.client_id,
                      ip=client_ip(request), helper=str(req.approved_by_id))
    db.commit()
    return {"ok": True, "redirect": redirect}


# ---------------------------------------------------------------- helper side

def _helper_req(db: Session, assist_id: uuid.UUID, ctx: Ctx):
    return assisted_service.load_for_helper(db, assist_id, ctx.user)


@router.get("/assist/{assist_id}/helper")
def helper_view(assist_id: uuid.UUID, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    req = _helper_req(db, assist_id, ctx)
    db.commit()
    return assisted_service.public_view(db, req, for_helper=True)


@router.post("/assist/{assist_id}/approve/options")
def approve_options(assist_id: uuid.UUID, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    req = _helper_req(db, assist_id, ctx)
    if req.status != "awaiting_helper":
        db.commit()
        raise HTTPException(400, f"This request is {req.status}")
    return RawResponse(content=webauthn_service.approval_options(db, ctx.user, req.id), media_type="application/json")


@router.post("/assist/{assist_id}/approve/verify")
def approve_verify(assist_id: uuid.UUID, body: ApproveVerify, request: Request,
                   ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    req = _helper_req(db, assist_id, ctx)
    webauthn_service.approval_verify(db, ctx.user, req.id, body.credential)  # helper's OWN passkey
    try:
        assisted_service.check_match(db, req, body.chosen)
    except AssistError:
        audit_service.log(db, "assist_wrong_number", actor_id=ctx.user.id, target_id=req.id, ip=client_ip(request))
        db.commit()
        raise
    assisted_service.approve(db, req, ctx.user)
    audit_service.log(db, "assist_approved", actor_id=ctx.user.id, target_id=req.id, client_id=req.client_id,
                      ip=client_ip(request), owner=str(req.owner_id))
    db.commit()
    return {"ok": True, "status": req.status}


@router.post("/assist/{assist_id}/reject")
def reject(assist_id: uuid.UUID, request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    req = _helper_req(db, assist_id, ctx)
    assisted_service.reject(db, req)
    audit_service.log(db, "assist_rejected", actor_id=ctx.user.id, target_id=req.id, ip=client_ip(request))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- demo SMS inbox

@router.get("/mock-phone/{phone}")
def mock_phone(phone: str, db: Session = Depends(get_db)):
    if not settings.DEMO_MODE:
        raise HTTPException(404, "Not found")
    rows = db.scalars(select(MockSMS).where(MockSMS.phone == phone).order_by(MockSMS.created_at.desc()).limit(10))
    return [{"message": m.message, "at": m.created_at.isoformat()} for m in rows]
