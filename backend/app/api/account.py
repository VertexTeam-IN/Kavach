"""The signed-in user's own account: profile, passkeys, sessions, recovery code, security score, logout."""
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, current, full_login
from ..models import AuthSession, Consent, Helper, OIDCClient, Passkey, User, utcnow
from ..schemas import PasskeyRename
from ..security import client_ip
from ..services import alert_service, audit_service, recovery_service
from ..services.authenticators import model_name
from ..services.session_service import logout as end_session

router = APIRouter(prefix="/api", tags=["account"])

STALE_DAYS = 90  # a passkey unused this long is probably an old phone or laptop


def _is_stale(p: Passkey) -> bool:
    return (p.last_used_at or p.created_at) < utcnow() - timedelta(days=STALE_DAYS)


@router.get("/me")
def me(ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    passkeys = db.scalar(select(func.count()).select_from(Passkey).where(Passkey.user_id == ctx.user.id)) or 0
    helper = db.get(User, ctx.session.assisted_by_id) if ctx.session.assisted_by_id else None
    return {
        "id": str(ctx.user.id),
        "username": ctx.user.username,
        "display_name": ctx.user.display_name,
        "phone_hint": _phone_hint(ctx.user.phone),
        "acr": ctx.session.acr,
        "is_assisted": ctx.is_assisted,
        "assisted_by": helper.display_name if helper else None,
        "session_expires_at": ctx.session.expires_at.isoformat(),
        "passkey_count": passkeys,
        "has_backup": passkeys >= 2,
        "has_recovery_code": recovery_service.has_code(db, ctx.user),
    }


def _phone_hint(phone: str | None) -> str | None:
    return f"••••••{phone[-4:]}" if phone and len(phone) >= 4 else None


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    end_session(db, request, response)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- passkeys

@router.get("/passkeys")
def list_passkeys(ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(select(Passkey).where(Passkey.user_id == ctx.user.id).order_by(Passkey.created_at))
    return [{
        "id": str(p.id),
        "label": p.label,
        "created_at": p.created_at.isoformat(),
        "last_used_at": p.last_used_at.isoformat() if p.last_used_at else None,
        "transports": p.transports,
        "synced": p.backed_up,
        "model": model_name(p.aaguid, p.transports),
        "stale": _is_stale(p),
    } for p in rows]


@router.patch("/passkeys/{passkey_id}")
def rename_passkey(passkey_id: uuid.UUID, body: PasskeyRename, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    p = db.get(Passkey, passkey_id)
    if not p or p.user_id != ctx.user.id:
        raise HTTPException(404, "Passkey not found")
    p.label = body.label
    db.commit()
    return {"ok": True}


@router.delete("/passkeys/{passkey_id}")
def delete_passkey(passkey_id: uuid.UUID, request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    p = db.get(Passkey, passkey_id)
    if not p or p.user_id != ctx.user.id:
        raise HTTPException(404, "Passkey not found")
    count = db.scalar(select(func.count()).select_from(Passkey).where(Passkey.user_id == ctx.user.id))
    if count <= 1:
        raise HTTPException(400, "You can't remove your only passkey. Add a backup passkey first.")
    db.delete(p)
    audit_service.log(db, "passkey_removed", actor_id=ctx.user.id, target_id=passkey_id, ip=client_ip(request))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- sessions

@router.get("/sessions")
def list_sessions(ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(select(AuthSession).where(
        AuthSession.user_id == ctx.user.id, AuthSession.revoked_at.is_(None), AuthSession.expires_at > utcnow(),
    ).order_by(AuthSession.created_at.desc()))
    return [{
        "id": str(s.id),
        "current": s.id == ctx.session.id,
        "acr": s.acr,
        "user_agent": s.user_agent,
        "created_at": s.created_at.isoformat(),
        "expires_at": s.expires_at.isoformat(),
    } for s in rows]


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: uuid.UUID, request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    s = db.get(AuthSession, session_id)
    if not s or s.user_id != ctx.user.id:
        raise HTTPException(404, "Session not found")
    s.revoked_at = utcnow()
    audit_service.log(db, "session_revoked", actor_id=ctx.user.id, target_id=session_id, ip=client_ip(request))
    db.commit()
    return {"ok": True}


@router.post("/sessions/revoke-others")
def revoke_other_sessions(request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    """Sign out everywhere except this browser."""
    n = alert_service.revoke_other_sessions(db, ctx.user.id, ctx.session.id)
    audit_service.log(db, "sessions_revoked_others", actor_id=ctx.user.id, ip=client_ip(request), count=n)
    db.commit()
    return {"ok": True, "signed_out": n}


# ---------------------------------------------------------------- connected websites

@router.get("/connected-sites")
def connected_sites(ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    rows = db.execute(select(Consent, OIDCClient).join(OIDCClient, OIDCClient.client_id == Consent.client_id)
                      .where(Consent.user_id == ctx.user.id))
    return [{"client_id": c.client_id, "name": cl.name, "scopes": c.scopes, "granted_at": c.granted_at.isoformat()}
            for c, cl in rows]


# ---------------------------------------------------------------- recovery code

@router.post("/recovery-code")
def regenerate_recovery_code(request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    code = recovery_service.issue_code(db, ctx.user)
    audit_service.log(db, "recovery_code_regenerated", actor_id=ctx.user.id, ip=client_ip(request))
    db.commit()
    return {"recovery_code": code}


# ---------------------------------------------------------------- security score

@router.get("/security-score")
def security_score(ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    """0–100, from things the user can fix themselves. Each check says how to fix it."""
    passkeys = list(db.scalars(select(Passkey).where(Passkey.user_id == ctx.user.id)))
    helpers = db.scalar(select(func.count()).select_from(Helper).where(
        Helper.owner_id == ctx.user.id, Helper.status == "active")) or 0
    stale = sum(_is_stale(p) for p in passkeys)
    warnings = alert_service.open_warnings(db, ctx.user.id)
    checks = [
        {"id": "backup", "label": "Two or more passkeys", "points": 30, "ok": len(passkeys) >= 2,
         "fix": "Add a backup passkey on your phone so losing one device doesn't lock you out."},
        {"id": "recovery", "label": "Recovery code saved", "points": 25, "ok": recovery_service.has_code(db, ctx.user),
         "fix": "Create a recovery code and keep it somewhere safe."},
        {"id": "helper", "label": "A trusted helper is set up", "points": 15, "ok": helpers > 0,
         "fix": "Invite someone you trust who can approve a sign-in when you can't use your passkey."},
        {"id": "fresh", "label": f"No passkeys unused for {STALE_DAYS}+ days", "points": 15, "ok": stale == 0,
         "fix": f"Remove {stale} old passkey{'s' if stale != 1 else ''} you no longer use."},
        {"id": "alerts", "label": "All security alerts reviewed", "points": 15, "ok": warnings == 0,
         "fix": f"Review {warnings} security alert{'s' if warnings != 1 else ''}: was it you?"},
    ]
    score = sum(c["points"] for c in checks if c["ok"])
    level = "strong" if score >= 85 else "good" if score >= 60 else "weak"
    return {"score": score, "level": level, "checks": checks}
