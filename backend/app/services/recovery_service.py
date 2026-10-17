"""Account recovery when every passkey is lost.

The lost private key can never be recovered. Instead the user proves ownership with
TWO things set up earlier — the one-time recovery code (saved at registration) AND an OTP
to their registered phone — and is then allowed to register ONE new passkey.
Afterwards all old passkeys and sessions are revoked and a fresh recovery code is issued.
"""
import uuid
from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Passkey, RecoveryCode, RecoveryRequest, User, utcnow
from ..security import (
    argon2_hash, argon2_verify, constant_eq, new_otp, new_recovery_code, new_token,
    normalize_recovery_code, sha256_hex,
)
from .assisted_service import send_sms
from .session_service import revoke_all_for_user

MAX_OTP_ATTEMPTS = 5


class RecoveryError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def issue_code(db: Session, user: User) -> str:
    """Create a new recovery code (shown to the user ONCE); older unused codes are invalidated."""
    db.execute(
        update(RecoveryCode)
        .where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))
        .values(used_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    code = new_recovery_code()
    db.add(RecoveryCode(user_id=user.id, code_hash=argon2_hash(normalize_recovery_code(code))))
    return code


def has_code(db: Session, user: User) -> bool:
    return db.scalar(select(RecoveryCode.id).where(
        RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))) is not None


def start(db: Session, username: str, code: str) -> tuple[RecoveryRequest, str]:
    generic = "Username or recovery code is incorrect."
    user = db.scalar(select(User).where(User.username == username))
    if not user or not user.phone:
        raise RecoveryError(generic)
    codes = list(db.scalars(select(RecoveryCode).where(
        RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))))
    match = next((c for c in codes if argon2_verify(c.code_hash, normalize_recovery_code(code))), None)
    if not match:
        raise RecoveryError(generic)

    otp, token = new_otp(), new_token()
    req = RecoveryRequest(
        user_id=user.id,
        recovery_code_id=match.id,
        token_hash=sha256_hex(token),
        otp_hash=sha256_hex(otp),
        expires_at=utcnow() + timedelta(seconds=settings.RECOVERY_TTL_SEC),
    )
    db.add(req)
    send_sms(db, user.phone, f"Kavach: your account recovery code is {otp}. If you did not request this, ignore it.")
    db.flush()
    return req, token


def load(db: Session, recovery_id: uuid.UUID, token: str | None) -> RecoveryRequest:
    req = db.get(RecoveryRequest, recovery_id)
    if (not req or not token or not constant_eq(req.token_hash, sha256_hex(token))
            or req.completed_at or req.expires_at <= utcnow()):
        raise RecoveryError("Recovery request not found or expired", 404)
    return req


def verify_otp(db: Session, req: RecoveryRequest, otp: str) -> None:
    if req.verified_at:
        return
    req.otp_attempts += 1
    if req.otp_attempts > MAX_OTP_ATTEMPTS:
        req.expires_at = utcnow()
        raise RecoveryError("Too many wrong codes. Start again.")
    if not constant_eq(req.otp_hash, sha256_hex(otp.strip())):
        raise RecoveryError("Wrong code")
    req.verified_at = utcnow()


def complete(db: Session, req: RecoveryRequest, user: User, new_passkey: Passkey) -> str:
    """Revoke every old passkey and session, burn the used code, issue a fresh code."""
    db.execute(
        delete(Passkey).where(Passkey.user_id == user.id, Passkey.id != new_passkey.id)
        .execution_options(synchronize_session=False)
    )
    revoke_all_for_user(db, user.id)
    req.completed_at = utcnow()
    return issue_code(db, user)


def recover_with_code(db: Session, username: str, code: str) -> tuple[User, str]:
    """Recover account using only username + recovery code without SMS OTP or new passkey."""
    generic = "Username or recovery code is incorrect."
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        raise RecoveryError(generic)
    codes = list(db.scalars(select(RecoveryCode).where(
        RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))))
    match = next((c for c in codes if argon2_verify(c.code_hash, normalize_recovery_code(code))), None)
    if not match:
        raise RecoveryError(generic)

    match.used_at = utcnow()
    db.execute(
        delete(Passkey).where(Passkey.user_id == user.id)
        .execution_options(synchronize_session=False)
    )
    revoke_all_for_user(db, user.id)
    db.execute(
        update(RecoveryRequest)
        .where(RecoveryRequest.user_id == user.id, RecoveryRequest.completed_at.is_(None))
        .values(completed_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    new_code = issue_code(db, user)
    return user, new_code

