"""SQLAlchemy models — one class per PostgreSQL table.

Security notes:
- Only public keys and hashes are stored. Session tokens, auth codes, challenges,
  OTPs and assist tokens are stored as SHA-256 hashes; client secrets and
  recovery codes as argon2 hashes.
- Every one-time item has expires_at + consumed_at/used_at so it can be consumed
  atomically exactly once.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Random 32-byte handle given to the authenticator as user.id (never the username)
    webauthn_user_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Passkey(Base):
    __tablename__ = "passkeys"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True, index=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)  # COSE-encoded public key
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[list] = mapped_column(JSONB, default=list)
    device_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # single_device / multi_device
    backed_up: Mapped[bool] = mapped_column(Boolean, default=False)
    label: Mapped[str] = mapped_column(String(64), default="Passkey")
    # Authenticator model id from the registration ("Windows Hello", "YubiKey 5", …). Added after
    # launch, so main.py adds the column to existing databases; NULL for older passkeys.
    aaguid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    challenge_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(32))  # register | login | add | assist_approve | recovery
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    acr: Mapped[str] = mapped_column(String(64))  # urn:kavach:acr:passkey | urn:kavach:acr:assisted
    amr: Mapped[list] = mapped_column(JSONB, default=list)
    assisted_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OIDCClient(Base):
    __tablename__ = "oidc_clients"

    client_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    secret_hash: Mapped[str | None] = mapped_column(Text, nullable=True)  # None for public clients
    redirect_uris: Mapped[list] = mapped_column(JSONB, default=list)
    post_logout_redirect_uris: Mapped[list] = mapped_column(JSONB, default=list)
    scopes: Mapped[list] = mapped_column(JSONB, default=lambda: ["openid", "profile"])
    allow_assisted: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthRequest(Base):
    """A pending /authorize request while the user signs in at Kavach."""
    __tablename__ = "auth_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(ForeignKey("oidc_clients.client_id", ondelete="CASCADE"))
    redirect_uri: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    nonce: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_challenge: Mapped[str] = mapped_column(String(128))
    code_challenge_method: Mapped[str] = mapped_column(String(16), default="S256")
    acr_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthCode(Base):
    __tablename__ = "auth_codes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("oidc_clients.client_id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    redirect_uri: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)
    nonce: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_challenge: Mapped[str] = mapped_column(String(128))
    acr: Mapped[str] = mapped_column(String(64))
    amr: Mapped[list] = mapped_column(JSONB, default=list)
    auth_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    assisted_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (UniqueConstraint("user_id", "client_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    client_id: Mapped[str] = mapped_column(ForeignKey("oidc_clients.client_id", ondelete="CASCADE"))
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Helper(Base):
    """Trusted-helper relationship: helper_id may approve assisted logins for owner_id."""
    __tablename__ = "helpers"
    __table_args__ = (UniqueConstraint("owner_id", "helper_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    helper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | active | revoked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssistedRequest(Base):
    __tablename__ = "assisted_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("oidc_clients.client_id"), nullable=True)
    auth_request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_requests.id"), nullable=True)
    owner_token_hash: Mapped[str] = mapped_column(String(64))
    otp_hash: Mapped[str] = mapped_column(String(64))
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0)
    otp_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    match_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    choices: Mapped[list] = mapped_column(JSONB, default=list)
    match_attempts: Mapped[int] = mapped_column(Integer, default=0)
    # otp_sent -> awaiting_helper -> approved -> consumed  (or rejected / cancelled / expired)
    status: Mapped[str] = mapped_column(String(24), default="otp_sent")
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecoveryCode(Base):
    __tablename__ = "recovery_codes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(Text)  # argon2
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecoveryRequest(Base):
    __tablename__ = "recovery_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recovery_code_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recovery_codes.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64))
    otp_hash: Mapped[str] = mapped_column(String(64))
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MockSMS(Base):
    """Demo-only SMS inbox (shown on /mock-phone). Replace with a real SMS gateway in production."""
    __tablename__ = "mock_sms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    """A security alert for the account owner, shown on the dashboard (simulated delivery: in-app
    only). Created from audit events by services/alert_service.py."""
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(48))            # the audit event that caused it
    severity: Mapped[str] = mapped_column(String(16))        # info | warn
    title: Mapped[str] = mapped_column(String(128))
    detail: Mapped[str] = mapped_column(Text, default="")
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # passkey / recovery request id
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(16), nullable=True)  # me | not_me


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
