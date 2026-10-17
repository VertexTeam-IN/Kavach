"""Trusted helpers: invite, accept, list, remove. Only full passkey sessions may change these."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, current, full_login
from ..models import Helper, User, utcnow
from ..schemas import HelperInvite
from ..security import client_ip
from ..services import assisted_service, audit_service

router = APIRouter(prefix="/api/helpers", tags=["helpers"])


def _person(u: User) -> dict:
    return {"username": u.username, "display_name": u.display_name}


@router.get("")
def list_helpers(ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(select(Helper).where(
        or_(Helper.owner_id == ctx.user.id, Helper.helper_id == ctx.user.id), Helper.status != "revoked"))
    my_helpers, helping, invitations = [], [], []
    for h in rows:
        if h.owner_id == ctx.user.id:
            my_helpers.append({"id": str(h.id), "status": h.status, **_person(db.get(User, h.helper_id))})
        elif h.status == "active":
            helping.append({"id": str(h.id), **_person(db.get(User, h.owner_id))})
        else:
            invitations.append({"id": str(h.id), **_person(db.get(User, h.owner_id))})
    return {"my_helpers": my_helpers, "helping": helping, "invitations": invitations}


@router.post("/invite")
def invite(body: HelperInvite, request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    helper = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    if not helper:
        raise HTTPException(404, "No Kavach user with that username")
    if helper.id == ctx.user.id:
        raise HTTPException(400, "You can't be your own helper")
    existing = db.scalar(select(Helper).where(Helper.owner_id == ctx.user.id, Helper.helper_id == helper.id))
    if existing and existing.status != "revoked":
        raise HTTPException(400, "Already invited")
    if existing:
        existing.status, existing.revoked_at, existing.created_at = "pending", None, utcnow()
        rel = existing
    else:
        rel = Helper(owner_id=ctx.user.id, helper_id=helper.id, status="pending")
        db.add(rel)
    db.flush()
    audit_service.log(db, "helper_invited", actor_id=ctx.user.id, target_id=helper.id, ip=client_ip(request))
    db.commit()
    return {"ok": True, "id": str(rel.id)}


@router.post("/{rel_id}/accept")
def accept(rel_id: uuid.UUID, request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    rel = db.get(Helper, rel_id)
    if not rel or rel.helper_id != ctx.user.id or rel.status != "pending":
        raise HTTPException(404, "Invitation not found")
    rel.status, rel.accepted_at = "active", utcnow()
    audit_service.log(db, "helper_accepted", actor_id=ctx.user.id, target_id=rel.owner_id, ip=client_ip(request))
    db.commit()
    return {"ok": True}


@router.delete("/{rel_id}")
def remove(rel_id: uuid.UUID, request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    rel = db.get(Helper, rel_id)
    if not rel or ctx.user.id not in (rel.owner_id, rel.helper_id):
        raise HTTPException(404, "Not found")
    rel.status, rel.revoked_at = "revoked", utcnow()
    audit_service.log(db, "helper_removed", actor_id=ctx.user.id, target_id=rel.id, ip=client_ip(request))
    db.commit()
    return {"ok": True}


@router.get("/requests")
def pending_requests(ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    """Assisted sign-in requests waiting for this helper's approval."""
    reqs = assisted_service.pending_for_helper(db, ctx.user)
    return [assisted_service.public_view(db, r, for_helper=True) for r in reqs]
