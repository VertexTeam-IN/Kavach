"""Security alerts for the account owner.

Alerts are created from audit events (audit_service.log calls from_event), so every place that
already records a security event gets an alert for free. Delivery is simulated: alerts are shown
on the dashboard only — no SMS, so the demo phone inbox keeps showing just one-time codes.

"This wasn't me" (report_not_me) is the owner's panic button for an alert: it signs out every
other session and undoes what the alert is about where that is safe.
"""
import re
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..models import Alert, AuthSession, Passkey, RecoveryRequest, User, utcnow

# Alerts about something an intruder could have done — these get the "This wasn't me" button.
REPORTABLE = {"login_success", "passkey_added", "recovery_started", "account_recovered", "assist_login"}


def device_name(ua: str | None) -> str:
    """Same wording as the dashboard's session list: 'Chrome on Windows'."""
    if not ua:
        return "An unknown device"
    browser = next((b for p, b in ((r"Edg/", "Edge"), (r"Chrome/", "Chrome"), (r"Firefox/", "Firefox"),
                                   (r"Safari/", "Safari")) if re.search(p, ua)), "A browser")
    os_ = next((o for p, o in ((r"Windows", "Windows"), (r"Android", "Android"), (r"iPhone|iPad", "iOS"),
                               (r"Mac OS", "macOS"), (r"Linux", "Linux")) if re.search(p, ua)), "")
    return f"{browser} on {os_}" if os_ else browser


def _as_uuid(value) -> uuid.UUID | None:
    """Alerts must never break the action that triggered them, so bad ids just mean 'unknown'."""
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value)) if value else None
    except ValueError:
        return None


def _add(db: Session, user_id, kind: str, severity: str, title: str, detail: str, *, target_id=None, ip=None):
    db.add(Alert(user_id=user_id, kind=kind, severity=severity, title=title, detail=detail,
                 target_id=str(target_id) if target_id else None, ip=ip))


def _newest_session(db: Session, user_id) -> AuthSession | None:
    return db.scalar(select(AuthSession).where(AuthSession.user_id == user_id)
                     .order_by(AuthSession.created_at.desc()).limit(1))


def _is_new_device(db: Session, sess: AuthSession) -> bool:
    seen = db.scalar(select(func.count()).select_from(AuthSession).where(
        AuthSession.user_id == sess.user_id, AuthSession.id != sess.id, AuthSession.user_agent == sess.user_agent))
    return not seen


def from_event(db: Session, event_type: str, *, actor_id, target_id, ip, meta: dict) -> None:
    if event_type == "login_success" and actor_id:
        sess = _newest_session(db, actor_id)
        if sess and _is_new_device(db, sess):     # only browsers this account has never used before
            _add(db, actor_id, event_type, "warn", "New sign-in from a new device",
                 f"{device_name(sess.user_agent)} signed in to your account with a passkey.", ip=ip)
    elif event_type == "passkey_added" and actor_id:
        _add(db, actor_id, event_type, "warn", "New passkey added",
             "A new passkey can now sign in to your account.", target_id=target_id, ip=ip)
    elif event_type == "passkey_removed" and actor_id:
        _add(db, actor_id, event_type, "info", "Passkey removed",
             "A passkey was removed from your account.", target_id=target_id, ip=ip)
    elif event_type == "recovery_started" and actor_id:
        _add(db, actor_id, event_type, "warn", "Account recovery started",
             "Someone entered your recovery code. If this wasn't you, stop it now and replace your code.",
             target_id=target_id, ip=ip)
    elif event_type == "account_recovered" and actor_id:
        _add(db, actor_id, event_type, "warn", "Account recovered on a new device",
             "Your old passkeys and sessions were signed out and a new passkey was created.", ip=ip)
    elif event_type == "assist_login" and actor_id:
        hid = _as_uuid(meta.get("helper"))
        helper = db.get(User, hid) if hid else None
        who = helper.display_name if helper else "Your trusted helper"
        _add(db, actor_id, event_type, "warn", "Signed in with help",
             f"{who} approved a view-only sign-in to your account.", ip=ip)
    elif event_type == "helper_accepted" and _as_uuid(target_id):
        helper = db.get(User, actor_id) if actor_id else None
        _add(db, _as_uuid(target_id), event_type, "info", "New trusted helper",
             f"{helper.display_name if helper else 'Someone'} can now approve assisted sign-ins for you.", ip=ip)
    elif event_type == "recovery_code_regenerated" and actor_id:
        _add(db, actor_id, event_type, "info", "New recovery code created",
             "Your previous recovery code no longer works.", ip=ip)


def open_warnings(db: Session, user_id) -> int:
    return db.scalar(select(func.count()).select_from(Alert).where(
        Alert.user_id == user_id, Alert.severity == "warn", Alert.resolved_at.is_(None))) or 0


def revoke_other_sessions(db: Session, user_id, keep_session_id) -> int:
    res = db.execute(update(AuthSession).where(
        AuthSession.user_id == user_id, AuthSession.id != keep_session_id,
        AuthSession.revoked_at.is_(None), AuthSession.expires_at > utcnow(),
    ).values(revoked_at=utcnow()))
    return res.rowcount or 0


def resolve(alert: Alert, resolution: str) -> None:
    now = utcnow()
    alert.resolved_at, alert.resolution = now, resolution
    alert.read_at = alert.read_at or now


def report_not_me(db: Session, alert: Alert, keep_session_id) -> list[str]:
    """Secure the account after the owner says an alert wasn't them. Returns what was done."""
    done = []
    n = revoke_other_sessions(db, alert.user_id, keep_session_id)
    done.append(f"Signed out {n} other session{'s' if n != 1 else ''}" if n else "No other sessions were signed in")

    if alert.kind == "passkey_added" and alert.target_id:
        pid = _as_uuid(alert.target_id)
        p = db.get(Passkey, pid) if pid else None
        if p and p.user_id == alert.user_id:
            count = db.scalar(select(func.count()).select_from(Passkey).where(Passkey.user_id == alert.user_id))
            if count > 1:
                db.delete(p)
                done.append("Removed the new passkey")

    if alert.kind == "recovery_started" and alert.target_id:
        rid = _as_uuid(alert.target_id)
        req = db.get(RecoveryRequest, rid) if rid else None
        if req and req.user_id == alert.user_id and not req.completed_at and req.expires_at > utcnow():
            req.expires_at = utcnow()
            done.append("Stopped the account recovery")

    if alert.kind in ("recovery_started", "account_recovered"):
        done.append("Replace your recovery code now — someone may know it")
    resolve(alert, "not_me")
    return done
