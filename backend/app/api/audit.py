"""The user's own security history."""
from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, current
from ..models import AuditEvent, OIDCClient, User

router = APIRouter(prefix="/api", tags=["audit"])

LABELS = {
    "user_registered": "Account created",
    "passkey_registered": "Passkey created",
    "passkey_added": "Backup passkey added",
    "passkey_removed": "Passkey removed",
    "login_success": "Signed in with passkey",
    "consent_granted": "Allowed a website",
    "consent_denied": "Denied a website",
    "session_revoked": "Session signed out",
    "helper_invited": "Helper invited",
    "helper_accepted": "Helper invitation accepted",
    "helper_removed": "Helper removed",
    "assist_requested": "Assisted sign-in requested",
    "assist_otp_verified": "Assisted sign-in: phone code verified",
    "assist_approved": "Assisted sign-in approved",
    "assist_rejected": "Assisted sign-in rejected",
    "assist_wrong_number": "Assisted sign-in: wrong number chosen",
    "assist_login": "Signed in with help",
    "assist_replay_blocked": "Blocked reuse of an approval",
    "recovery_started": "Account recovery started",
    "account_recovered": "Account recovered on a new device",
    "recovery_code_regenerated": "New recovery code created",
    "sessions_revoked_others": "Signed out all other sessions",
    "alert_reported_not_me": "Reported activity as \"not me\"",
}


@router.get("/audit")
def my_audit(ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(AuditEvent)
        .where(or_(AuditEvent.actor_id == ctx.user.id, AuditEvent.target_id == str(ctx.user.id)))
        .order_by(AuditEvent.created_at.desc())
        .limit(50)
    )
    out = []
    for e in rows:
        actor = db.get(User, e.actor_id) if e.actor_id else None
        client = db.get(OIDCClient, e.client_id) if e.client_id else None
        out.append({
            "id": str(e.id),
            "event": e.event_type,
            "label": LABELS.get(e.event_type, e.event_type.replace("_", " ").capitalize()),
            "by": actor.display_name if actor and actor.id != ctx.user.id else None,
            "website": client.name if client else None,
            "ip": e.ip,
            "at": e.created_at.isoformat(),
        })
    return out
