"""Kavach login sessions (the kavach_sid cookie)."""
from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AuthSession, User, utcnow
from ..security import clear_session_cookie, new_token, set_session_cookie, sha256_hex

ACR_PASSKEY = "urn:kavach:acr:passkey"
ACR_ASSISTED = "urn:kavach:acr:assisted"


def find_session(db: Session, request: Request) -> AuthSession | None:
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        return None
    return db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == sha256_hex(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utcnow(),
        )
    )


def create_session(
    db: Session,
    request: Request,
    response: Response,
    user: User,
    *,
    acr: str = ACR_PASSKEY,
    amr: list[str] | None = None,
    assisted_by_id=None,
) -> AuthSession:
    """Create a new session and set the cookie. Any session the browser already had is revoked
    (session rotation after authentication)."""
    old = find_session(db, request)
    if old:
        old.revoked_at = utcnow()

    ttl_min = settings.ASSISTED_SESSION_TTL_MIN if acr == ACR_ASSISTED else settings.SESSION_TTL_MIN
    token = new_token()
    sess = AuthSession(
        user_id=user.id,
        token_hash=sha256_hex(token),
        acr=acr,
        amr=amr or (["hwk", "user"] if acr == ACR_PASSKEY else ["otp", "helper"]),
        assisted_by_id=assisted_by_id,
        user_agent=(request.headers.get("user-agent") or "")[:250],
        expires_at=utcnow() + timedelta(minutes=ttl_min),
    )
    db.add(sess)
    db.flush()
    set_session_cookie(response, token, ttl_min * 60)
    return sess


def revoke_session(db: Session, sess: AuthSession) -> None:
    sess.revoked_at = utcnow()


def revoke_all_for_user(db: Session, user_id) -> None:
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def logout(db: Session, request: Request, response: Response) -> None:
    sess = find_session(db, request)
    if sess:
        revoke_session(db, sess)
    clear_session_cookie(response)
