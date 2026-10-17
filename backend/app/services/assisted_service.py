"""Assisted access: a trusted helper approves ONE login for an owner who cannot use a passkey.

Flow
  1. Owner: POST /api/assist {username, req?}       -> OTP sent to owner's phone, owner gets a private token
  2. Owner: POST /api/assist/{id}/otp {otp}         -> match number shown to owner (3-minute window starts)
  3. Helper (signed in with own passkey): sees request + 3 numbers, picks the one the owner reads out,
     approves with their own passkey               -> status = approved
  4. Owner: POST /api/assist/{id}/complete          -> atomically consumed once; owner gets a short
     assisted session (acr=assisted), and the website gets acr/amr saying so.

Guarantees: single use, expiry, number matching, max 5 OTP tries, max 2 wrong numbers,
helper must be an active helper of this owner, helper never gets the owner's session or credentials.
"""
import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AssistedRequest, AuthRequest, Helper, MockSMS, OIDCClient, User, utcnow
from ..security import constant_eq, new_match_code_and_choices, new_otp, new_token, sha256_hex

MAX_OTP_ATTEMPTS = 5
MAX_MATCH_ATTEMPTS = 2
TERMINAL = {"consumed", "rejected", "cancelled", "expired"}


class AssistError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def send_sms(db: Session, phone: str, message: str) -> None:
    """Demo SMS gateway: stores the message for the /mock-phone page."""
    db.add(MockSMS(phone=phone, message=message))


def active_helpers(db: Session, owner_id) -> list[Helper]:
    return list(db.scalars(select(Helper).where(Helper.owner_id == owner_id, Helper.status == "active")))


def _expire_if_needed(req: AssistedRequest) -> None:
    if req.status not in TERMINAL and req.expires_at <= utcnow():
        req.status = "expired"


def start(db: Session, username: str, auth_req: AuthRequest | None) -> tuple[AssistedRequest, str]:
    owner = db.scalar(select(User).where(User.username == username))
    # Same message for unknown user / no helper / no phone so usernames can't be probed
    generic = "Assisted sign-in is not available for this account."
    if not owner or not owner.phone or not active_helpers(db, owner.id):
        raise AssistError(generic)
    if auth_req:
        client = db.get(OIDCClient, auth_req.client_id)
        from .oidc_service import assisted_allowed
        if not assisted_allowed(client, auth_req):
            raise AssistError(f"{client.name} does not allow assisted sign-in. Please use a passkey.")

    otp = new_otp()
    owner_token = new_token()
    req = AssistedRequest(
        owner_id=owner.id,
        client_id=auth_req.client_id if auth_req else None,
        auth_request_id=auth_req.id if auth_req else None,
        owner_token_hash=sha256_hex(owner_token),
        otp_hash=sha256_hex(otp),
        status="otp_sent",
        expires_at=utcnow() + timedelta(seconds=settings.ASSIST_OTP_TTL_SEC),
    )
    db.add(req)
    send_sms(db, owner.phone, f"Kavach: your assisted sign-in code is {otp}. Never share it with anyone.")
    db.flush()
    return req, owner_token


def load_for_owner(db: Session, assist_id: uuid.UUID, owner_token: str | None) -> AssistedRequest:
    req = db.get(AssistedRequest, assist_id)
    if not req or not owner_token or not constant_eq(req.owner_token_hash, sha256_hex(owner_token)):
        raise AssistError("Request not found", 404)
    _expire_if_needed(req)
    return req


def verify_otp(db: Session, req: AssistedRequest, otp: str) -> AssistedRequest:
    if req.status != "otp_sent":
        raise AssistError("This request is no longer waiting for a code")
    req.otp_attempts += 1
    if req.otp_attempts > MAX_OTP_ATTEMPTS:
        req.status = "cancelled"
        raise AssistError("Too many wrong codes. Start again.")
    if not constant_eq(req.otp_hash, sha256_hex(otp.strip())):
        raise AssistError("Wrong code")
    code, choices = new_match_code_and_choices()
    req.otp_verified_at = utcnow()
    req.match_code = code
    req.choices = choices
    req.status = "awaiting_helper"
    req.expires_at = utcnow() + timedelta(seconds=settings.ASSIST_APPROVAL_TTL_SEC)
    return req


def load_for_helper(db: Session, assist_id: uuid.UUID, helper: User) -> AssistedRequest:
    req = db.get(AssistedRequest, assist_id)
    if not req:
        raise AssistError("Request not found", 404)
    rel = db.scalar(select(Helper).where(
        Helper.owner_id == req.owner_id, Helper.helper_id == helper.id, Helper.status == "active"))
    if not rel:
        raise AssistError("You are not a trusted helper for this person", 403)
    _expire_if_needed(req)
    return req


def pending_for_helper(db: Session, helper: User) -> list[AssistedRequest]:
    owner_ids = [h.owner_id for h in db.scalars(
        select(Helper).where(Helper.helper_id == helper.id, Helper.status == "active"))]
    if not owner_ids:
        return []
    reqs = list(db.scalars(select(AssistedRequest).where(
        AssistedRequest.owner_id.in_(owner_ids),
        AssistedRequest.status == "awaiting_helper",
        AssistedRequest.expires_at > utcnow(),
    ).order_by(AssistedRequest.created_at.desc())))
    return reqs


def check_match(db: Session, req: AssistedRequest, chosen: str) -> None:
    """Called after the helper's passkey verified. Wrong number twice cancels the request."""
    if req.status != "awaiting_helper":
        raise AssistError("This request can no longer be approved")
    if not constant_eq(str(chosen), req.match_code or ""):
        req.match_attempts += 1
        if req.match_attempts >= MAX_MATCH_ATTEMPTS:
            req.status = "cancelled"
            raise AssistError("Wrong number again — request cancelled for safety.")
        raise AssistError("That number doesn't match what the person sees. Ask them to read it again.")


def approve(db: Session, req: AssistedRequest, helper: User) -> None:
    req.status = "approved"
    req.approved_by_id = helper.id
    req.approved_at = utcnow()


def reject(db: Session, req: AssistedRequest) -> None:
    if req.status in TERMINAL:
        raise AssistError("Request already finished")
    req.status = "rejected"


def consume(db: Session, req: AssistedRequest) -> bool:
    """Atomically move approved -> consumed. Returns False if already used / expired."""
    row = db.scalar(
        update(AssistedRequest)
        .where(AssistedRequest.id == req.id, AssistedRequest.status == "approved",
               AssistedRequest.consumed_at.is_(None), AssistedRequest.expires_at > utcnow())
        .values(status="consumed", consumed_at=utcnow())
        .returning(AssistedRequest.id)
        .execution_options(synchronize_session=False)
    )
    if row is not None:
        db.refresh(req)
    return row is not None


def public_view(db: Session, req: AssistedRequest, *, for_helper: bool) -> dict:
    owner = db.get(User, req.owner_id)
    client = db.get(OIDCClient, req.client_id) if req.client_id else None
    helper = db.get(User, req.approved_by_id) if req.approved_by_id else None
    data = {
        "id": str(req.id),
        "status": req.status,
        "owner": {"username": owner.username, "display_name": owner.display_name},
        "website": client.name if client else "Kavach account (view only)",
        "expires_at": req.expires_at.isoformat(),
        "approved_by": helper.display_name if helper else None,
    }
    if for_helper:
        data["choices"] = req.choices if req.status == "awaiting_helper" else []
        data["scopes"] = ["Your name", "Your username"] if client else []
    else:
        data["match_code"] = req.match_code if req.status == "awaiting_helper" else None
    return data
