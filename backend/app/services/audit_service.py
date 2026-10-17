"""Security audit log. Never pass secrets (OTPs, codes, tokens, keys) in meta.
Events that matter to the account owner also become alerts (alert_service), in the same transaction."""
import uuid

from sqlalchemy.orm import Session

from ..models import AuditEvent
from . import alert_service


def log(
    db: Session,
    event_type: str,
    *,
    actor_id: uuid.UUID | None = None,
    target_id: uuid.UUID | str | None = None,
    client_id: str | None = None,
    ip: str | None = None,
    commit: bool = False,
    **meta,
) -> None:
    clean = {k: v for k, v in meta.items() if v is not None}
    db.add(AuditEvent(
        actor_id=actor_id,
        event_type=event_type,
        target_id=str(target_id) if target_id else None,
        client_id=client_id,
        ip=ip,
        meta=clean,
    ))
    alert_service.from_event(db, event_type, actor_id=actor_id, target_id=target_id, ip=ip, meta=clean)
    if commit:
        db.commit()
