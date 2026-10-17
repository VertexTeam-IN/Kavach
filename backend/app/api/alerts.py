"""The signed-in user's security alerts, and the "This wasn't me" button."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, current, full_login
from ..models import Alert, utcnow
from ..security import client_ip
from ..services import alert_service, audit_service

router = APIRouter(prefix="/api", tags=["alerts"])


def _own(db: Session, ctx: Ctx, alert_id: uuid.UUID) -> Alert:
    a = db.get(Alert, alert_id)
    if not a or a.user_id != ctx.user.id:
        raise HTTPException(404, "Alert not found")
    return a


@router.get("/alerts")
def list_alerts(ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(select(Alert).where(Alert.user_id == ctx.user.id).order_by(Alert.created_at.desc()).limit(30))
    unread = db.scalar(select(func.count()).select_from(Alert).where(
        Alert.user_id == ctx.user.id, Alert.read_at.is_(None))) or 0
    return {
        "unread": unread,
        "open_warnings": alert_service.open_warnings(db, ctx.user.id),
        "items": [{
            "id": str(a.id),
            "kind": a.kind,
            "severity": a.severity,
            "title": a.title,
            "detail": a.detail,
            "ip": a.ip,
            "at": a.created_at.isoformat(),
            "read": a.read_at is not None,
            "resolution": a.resolution,
            "can_report": a.kind in alert_service.REPORTABLE and a.resolved_at is None,
        } for a in rows],
    }


@router.post("/alerts/read")
def mark_all_read(ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    for a in db.scalars(select(Alert).where(Alert.user_id == ctx.user.id, Alert.read_at.is_(None))):
        a.read_at = utcnow()
    db.commit()
    return {"ok": True}


@router.post("/alerts/{alert_id}/me")
def confirm_me(alert_id: uuid.UUID, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    alert_service.resolve(_own(db, ctx, alert_id), "me")
    db.commit()
    return {"ok": True}


@router.post("/alerts/{alert_id}/not-me")
def report_not_me(alert_id: uuid.UUID, request: Request, ctx: Ctx = Depends(full_login), db: Session = Depends(get_db)):
    a = _own(db, ctx, alert_id)
    if a.kind not in alert_service.REPORTABLE or a.resolved_at:
        raise HTTPException(400, "This alert can't be reported")
    done = alert_service.report_not_me(db, a, ctx.session.id)
    audit_service.log(db, "alert_reported_not_me", actor_id=ctx.user.id, target_id=a.id, ip=client_ip(request),
                      alert=a.kind)
    db.commit()
    return {"ok": True, "done": done}
