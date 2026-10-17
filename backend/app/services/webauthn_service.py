"""Passkey registration and authentication (WebAuthn / FIDO2) using py_webauthn.

Challenge handling:
  * Every ceremony gets a fresh 32-byte random challenge from py_webauthn.
  * Only its SHA-256 hash is stored, with a purpose, an owner and a 2-minute expiry.
  * On verify, the challenge is read back out of the signed clientDataJSON, hashed,
    and consumed with one atomic UPDATE ... WHERE consumed_at IS NULL RETURNING.
    A second use (replay) finds nothing and is rejected.
"""
import json
import os
import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ..config import settings
from ..models import Challenge, Passkey, User, utcnow
from ..security import sha256_hex

TIMEOUT_MS = 120_000
ALGS = [COSEAlgorithmIdentifier.ECDSA_SHA_256, COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256]


class WebAuthnError(Exception):
    """Raised for any passkey verification failure. Mapped to HTTP 400."""


# ---------------------------------------------------------------- challenges

def _save_challenge(db: Session, challenge: bytes, purpose: str, user_id=None, context: dict | None = None) -> None:
    db.add(Challenge(
        challenge_hash=sha256_hex(challenge),
        purpose=purpose,
        user_id=user_id,
        context=context or {},
        expires_at=utcnow() + timedelta(seconds=settings.CHALLENGE_TTL_SEC),
    ))


def _challenge_from_credential(credential: dict) -> bytes:
    try:
        client_data = json.loads(base64url_to_bytes(credential["response"]["clientDataJSON"]))
        return base64url_to_bytes(client_data["challenge"])
    except Exception as exc:  # malformed input
        raise WebAuthnError("Malformed passkey response") from exc


def _consume_challenge(db: Session, credential: dict, purpose: str) -> tuple[Challenge, bytes]:
    """Atomically mark the challenge used. Returns the row and the raw challenge bytes."""
    challenge = _challenge_from_credential(credential)
    row_id = db.scalar(
        update(Challenge)
        .where(
            Challenge.challenge_hash == sha256_hex(challenge),
            Challenge.purpose == purpose,
            Challenge.consumed_at.is_(None),
            Challenge.expires_at > utcnow(),
        )
        .values(consumed_at=utcnow())
        .returning(Challenge.id)
        .execution_options(synchronize_session=False)
    )
    if row_id is None:
        db.rollback()
        raise WebAuthnError("This sign-in attempt expired or was already used. Please try again.")
    return db.get(Challenge, row_id), challenge


# ---------------------------------------------------------------- registration

def _registration_options(
    db: Session, *, purpose: str, user_handle: bytes, username: str, display_name: str,
    user_id=None, context: dict | None = None, exclude: list[Passkey] | None = None,
) -> str:
    options = generate_registration_options(
        rp_id=settings.RP_ID,
        rp_name=settings.RP_NAME,
        user_id=user_handle,
        user_name=username,
        user_display_name=display_name,
        timeout=TIMEOUT_MS,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        supported_pub_key_algs=ALGS,
        exclude_credentials=[PublicKeyCredentialDescriptor(id=p.credential_id) for p in (exclude or [])],
    )
    _save_challenge(db, options.challenge, purpose, user_id=user_id, context=context)
    db.commit()
    return options_to_json(options)


def _verify_registration(db: Session, credential: dict, purpose: str):
    ch, challenge = _consume_challenge(db, credential, purpose)
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin=settings.ORIGIN,
            expected_rp_id=settings.RP_ID,
            require_user_verification=True,
        )
    except Exception as exc:
        db.commit()  # keep the challenge consumed
        raise WebAuthnError(f"Passkey could not be verified: {exc}") from exc
    if db.scalar(select(Passkey.id).where(Passkey.credential_id == verified.credential_id)):
        db.commit()
        raise WebAuthnError("This passkey is already registered")
    return ch, verified


def _passkey_from(verified, user_id, credential: dict, label: str) -> Passkey:
    device_type = getattr(verified, "credential_device_type", None)
    return Passkey(
        user_id=user_id,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        transports=list(credential.get("response", {}).get("transports") or []),
        device_type=getattr(device_type, "value", device_type),
        backed_up=bool(getattr(verified, "credential_backed_up", False)),
        label=label,
        aaguid=getattr(verified, "aaguid", None),
    )


def register_options(db: Session, username: str, display_name: str, phone: str | None) -> str:
    if db.scalar(select(User.id).where(User.username == username)):
        raise WebAuthnError("That username is taken")
    user_handle = os.urandom(32)
    return _registration_options(
        db, purpose="register", user_handle=user_handle, username=username, display_name=display_name,
        context={"username": username, "display_name": display_name, "phone": phone,
                 "user_handle": bytes_to_base64url(user_handle)},
    )


def register_verify(db: Session, credential: dict, label: str = "This device") -> tuple[User, Passkey]:
    ch, verified = _verify_registration(db, credential, "register")
    ctx = ch.context
    if db.scalar(select(User.id).where(User.username == ctx["username"])):
        db.commit()
        raise WebAuthnError("That username is taken")
    user = User(
        username=ctx["username"],
        display_name=ctx["display_name"],
        phone=ctx.get("phone"),
        webauthn_user_id=base64url_to_bytes(ctx["user_handle"]),
    )
    db.add(user)
    db.flush()
    passkey = _passkey_from(verified, user.id, credential, label)
    db.add(passkey)
    db.flush()
    return user, passkey


def add_options(db: Session, user: User, purpose: str = "add", context: dict | None = None) -> str:
    """Options to add another passkey (backup device, or new device during recovery)."""
    existing = list(db.scalars(select(Passkey).where(Passkey.user_id == user.id)))
    return _registration_options(
        db, purpose=purpose, user_handle=user.webauthn_user_id, username=user.username,
        display_name=user.display_name, user_id=user.id, context=context, exclude=existing,
    )


def add_verify(db: Session, user: User, credential: dict, purpose: str = "add", label: str = "Backup passkey") -> tuple[Passkey, Challenge]:
    ch, verified = _verify_registration(db, credential, purpose)
    if ch.user_id != user.id:
        db.commit()
        raise WebAuthnError("This registration belongs to a different account")
    passkey = _passkey_from(verified, user.id, credential, label)
    db.add(passkey)
    db.flush()
    return passkey, ch


# ---------------------------------------------------------------- authentication

def login_options(db: Session) -> str:
    """Discoverable-credential login: no username, the authenticator picks the account."""
    options = generate_authentication_options(
        rp_id=settings.RP_ID,
        timeout=TIMEOUT_MS,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    _save_challenge(db, options.challenge, "login")
    db.commit()
    return options_to_json(options)


def _verify_assertion(db: Session, credential: dict, purpose: str) -> tuple[Challenge, User, Passkey]:
    ch, challenge = _consume_challenge(db, credential, purpose)
    try:
        raw_id = base64url_to_bytes(credential["rawId"])
    except Exception as exc:
        db.commit()
        raise WebAuthnError("Malformed passkey response") from exc
    passkey = db.scalar(select(Passkey).where(Passkey.credential_id == raw_id))
    if not passkey:
        db.commit()
        raise WebAuthnError("Unknown passkey. It may have been removed — register again or use your backup.")
    user = db.get(User, passkey.user_id)

    user_handle = (credential.get("response") or {}).get("userHandle")
    if user_handle and base64url_to_bytes(user_handle) != user.webauthn_user_id:
        db.commit()
        raise WebAuthnError("Passkey does not match this account")

    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin=settings.ORIGIN,
            expected_rp_id=settings.RP_ID,
            credential_public_key=passkey.public_key,
            credential_current_sign_count=passkey.sign_count,
            require_user_verification=True,
        )
    except Exception as exc:
        db.commit()
        raise WebAuthnError(f"Passkey could not be verified: {exc}") from exc

    passkey.sign_count = verified.new_sign_count
    passkey.last_used_at = utcnow()
    return ch, user, passkey


def login_verify(db: Session, credential: dict) -> tuple[User, Passkey]:
    _, user, passkey = _verify_assertion(db, credential, "login")
    return user, passkey


def approval_options(db: Session, helper: User, assist_id: uuid.UUID) -> str:
    """A helper approving an assisted request must use one of *their own* passkeys."""
    creds = list(db.scalars(select(Passkey).where(Passkey.user_id == helper.id)))
    if not creds:
        raise WebAuthnError("You have no passkey registered")
    options = generate_authentication_options(
        rp_id=settings.RP_ID,
        timeout=TIMEOUT_MS,
        user_verification=UserVerificationRequirement.REQUIRED,
        allow_credentials=[PublicKeyCredentialDescriptor(id=p.credential_id) for p in creds],
    )
    _save_challenge(db, options.challenge, "assist_approve", user_id=helper.id, context={"assist_id": str(assist_id)})
    db.commit()
    return options_to_json(options)


def approval_verify(db: Session, helper: User, assist_id: uuid.UUID, credential: dict) -> Passkey:
    ch, user, passkey = _verify_assertion(db, credential, "assist_approve")
    if ch.user_id != helper.id or ch.context.get("assist_id") != str(assist_id) or user.id != helper.id:
        db.commit()
        raise WebAuthnError("Approval must be signed with your own passkey for this exact request")
    return passkey
