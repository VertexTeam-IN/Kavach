"""OpenID Connect provider logic: Authorization Code flow with PKCE (S256), RS256 tokens."""
import base64
import hashlib
import uuid
from datetime import timedelta
from urllib.parse import unquote, urlencode, urlsplit, urlunsplit

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import settings
from ..keys import sign_jwt
from ..models import AuthCode, AuthRequest, AuthSession, Consent, OIDCClient, User, utcnow
from ..security import argon2_verify, constant_eq, new_token, sha256_hex
from .session_service import ACR_ASSISTED, ACR_PASSKEY

SUPPORTED_SCOPES = ["openid", "profile"]


class OIDCError(Exception):
    def __init__(self, error: str, description: str, status: int = 400):
        super().__init__(description)
        self.error = error
        self.description = description
        self.status = status


class RedirectableError(OIDCError):
    def __init__(self, auth_req: AuthRequest, error: str, description: str):
        super().__init__(error, description)
        self.auth_req = auth_req


# ---------------------------------------------------------------- helpers

def add_query(url: str, params: dict) -> str:
    parts = urlsplit(url)
    extra = urlencode({k: v for k, v in params.items() if v is not None})
    query = f"{parts.query}&{extra}" if parts.query else extra
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def discovery() -> dict:
    iss = settings.ISSUER
    return {
        "issuer": iss,
        "authorization_endpoint": f"{iss}/authorize",
        "token_endpoint": f"{iss}/token",
        "userinfo_endpoint": f"{iss}/userinfo",
        "jwks_uri": f"{iss}/.well-known/jwks.json",
        "end_session_endpoint": f"{iss}/logout",
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": SUPPORTED_SCOPES,
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
        "code_challenge_methods_supported": ["S256"],
        "claims_supported": ["sub", "iss", "aud", "exp", "iat", "auth_time", "nonce", "acr", "amr",
                             "name", "preferred_username", "kavach_assisted_by"],
        "acr_values_supported": [ACR_PASSKEY, ACR_ASSISTED],
        "claims_parameter_supported": False,
        "request_parameter_supported": False,
    }


def get_client(db: Session, client_id: str | None) -> OIDCClient | None:
    if not client_id:
        return None
    return db.get(OIDCClient, client_id)


def assisted_allowed(client: OIDCClient, auth_req: AuthRequest | None) -> bool:
    """A website can disable assisted logins entirely, or demand a passkey via acr_values."""
    if not client.allow_assisted:
        return False
    if auth_req and auth_req.acr_values:
        values = auth_req.acr_values.split()
        if ACR_PASSKEY in values and ACR_ASSISTED not in values:
            return False
    return True


def granted_scopes(client: OIDCClient, requested: str) -> list[str]:
    return [s for s in requested.split() if s in client.scopes and s in SUPPORTED_SCOPES]


# ---------------------------------------------------------------- /authorize

def start_authorization(db: Session, params: dict) -> AuthRequest:
    """Validate an /authorize request. Errors that must NOT redirect (bad client or redirect URI)
    raise OIDCError; the caller shows an error page instead of redirecting."""
    client = get_client(db, params.get("client_id"))
    if not client:
        raise OIDCError("invalid_client", "Unknown client_id")
    redirect_uri = params.get("redirect_uri")
    if not redirect_uri or redirect_uri not in client.redirect_uris:
        raise OIDCError("invalid_request", "redirect_uri is not registered for this client")

    auth_req = AuthRequest(
        client_id=client.client_id,
        redirect_uri=redirect_uri,
        scope=params.get("scope") or "",
        state=params.get("state"),
        nonce=params.get("nonce"),
        code_challenge=params.get("code_challenge") or "",
        code_challenge_method=params.get("code_challenge_method") or "plain",
        acr_values=params.get("acr_values"),
        prompt=params.get("prompt"),
        expires_at=utcnow() + timedelta(seconds=settings.AUTH_REQUEST_TTL_SEC),
    )
    # Errors below are safe to return to the (verified) redirect_uri
    if params.get("response_type") != "code":
        raise RedirectableError(auth_req, "unsupported_response_type", "Only response_type=code is supported")
    if "openid" not in auth_req.scope.split():
        raise RedirectableError(auth_req, "invalid_scope", "scope must include openid")
    if not auth_req.code_challenge or auth_req.code_challenge_method != "S256":
        raise RedirectableError(auth_req, "invalid_request", "PKCE with code_challenge_method=S256 is required")

    db.add(auth_req)
    db.commit()
    return auth_req


def error_redirect(auth_req: AuthRequest, error: str, description: str) -> str:
    return add_query(auth_req.redirect_uri, {"error": error, "error_description": description, "state": auth_req.state})


def load_auth_request(db: Session, req_id: str | uuid.UUID) -> AuthRequest:
    try:
        rid = uuid.UUID(str(req_id))
    except ValueError as exc:
        raise OIDCError("invalid_request", "Unknown sign-in request") from exc
    auth_req = db.get(AuthRequest, rid)
    if not auth_req or auth_req.completed_at is not None or auth_req.expires_at <= utcnow():
        raise OIDCError("invalid_request", "This sign-in request expired. Go back to the website and try again.")
    return auth_req


def has_consent(db: Session, user_id, client: OIDCClient, scopes: list[str]) -> bool:
    c = db.scalar(select(Consent).where(Consent.user_id == user_id, Consent.client_id == client.client_id))
    return bool(c) and set(scopes) <= set(c.scopes)


def save_consent(db: Session, user_id, client: OIDCClient, scopes: list[str]) -> None:
    c = db.scalar(select(Consent).where(Consent.user_id == user_id, Consent.client_id == client.client_id))
    if c:
        c.scopes = sorted(set(c.scopes) | set(scopes))
        c.granted_at = utcnow()
    else:
        db.add(Consent(user_id=user_id, client_id=client.client_id, scopes=scopes))


def issue_code(db: Session, auth_req: AuthRequest, sess: AuthSession) -> str:
    """Create a 60-second single-use authorization code and return the redirect URL."""
    client = db.get(OIDCClient, auth_req.client_id)
    scopes = granted_scopes(client, auth_req.scope)
    code = new_token()
    db.add(AuthCode(
        code_hash=sha256_hex(code),
        client_id=auth_req.client_id,
        user_id=sess.user_id,
        redirect_uri=auth_req.redirect_uri,
        scope=" ".join(scopes),
        nonce=auth_req.nonce,
        code_challenge=auth_req.code_challenge,
        acr=sess.acr,
        amr=sess.amr,
        auth_time=sess.created_at,
        assisted_by_id=sess.assisted_by_id,
        expires_at=utcnow() + timedelta(seconds=settings.AUTH_CODE_TTL_SEC),
    ))
    auth_req.completed_at = utcnow()
    return add_query(auth_req.redirect_uri, {"code": code, "state": auth_req.state, "iss": settings.ISSUER})


# ---------------------------------------------------------------- /token

def authenticate_client(db: Session, form: dict, authorization: str | None) -> OIDCClient:
    client_id, client_secret = form.get("client_id"), form.get("client_secret")
    if authorization and authorization.lower().startswith("basic "):
        try:
            raw = base64.b64decode(authorization[6:]).decode()
            cid, _, secret = raw.partition(":")
            client_id, client_secret = unquote(cid), unquote(secret)
        except Exception as exc:
            raise OIDCError("invalid_client", "Malformed Authorization header", 401) from exc
    client = get_client(db, client_id)
    if not client:
        raise OIDCError("invalid_client", "Unknown client", 401)
    if not client.is_public and not argon2_verify(client.secret_hash, client_secret or ""):
        raise OIDCError("invalid_client", "Client authentication failed", 401)
    return client


def _pkce_ok(verifier: str | None, challenge: str) -> bool:
    if not verifier or not (43 <= len(verifier) <= 128):
        return False
    computed = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return constant_eq(computed, challenge)


def exchange_code(db: Session, client: OIDCClient, form: dict) -> dict:
    if form.get("grant_type") != "authorization_code":
        raise OIDCError("unsupported_grant_type", "Only authorization_code is supported")
    code = form.get("code") or ""
    row_id = db.scalar(
        update(AuthCode)
        .where(AuthCode.code_hash == sha256_hex(code), AuthCode.consumed_at.is_(None), AuthCode.expires_at > utcnow())
        .values(consumed_at=utcnow())
        .returning(AuthCode.id)
        .execution_options(synchronize_session=False)
    )
    if row_id is None:
        db.rollback()
        raise OIDCError("invalid_grant", "Authorization code is invalid, expired or already used")
    ac = db.get(AuthCode, row_id)
    if ac.client_id != client.client_id:
        db.commit()
        raise OIDCError("invalid_grant", "Code was issued to a different client")
    if form.get("redirect_uri") != ac.redirect_uri:
        db.commit()
        raise OIDCError("invalid_grant", "redirect_uri does not match")
    if not _pkce_ok(form.get("code_verifier"), ac.code_challenge):
        db.commit()
        raise OIDCError("invalid_grant", "PKCE verification failed")

    user = db.get(User, ac.user_id)
    helper = db.get(User, ac.assisted_by_id) if ac.assisted_by_id else None
    now = int(utcnow().timestamp())
    scopes = ac.scope.split()

    id_claims = {
        "iss": settings.ISSUER,
        "sub": str(user.id),
        "aud": client.client_id,
        "azp": client.client_id,
        "iat": now,
        "exp": now + settings.ID_TOKEN_TTL_SEC,
        "auth_time": int(ac.auth_time.timestamp()),
        "acr": ac.acr,
        "amr": ac.amr,
    }
    if ac.nonce:
        id_claims["nonce"] = ac.nonce
    if "profile" in scopes:
        id_claims["name"] = user.display_name
        id_claims["preferred_username"] = user.username
    if helper:
        id_claims["kavach_assisted_by"] = helper.display_name

    access_claims = {
        "iss": settings.ISSUER,
        "sub": str(user.id),
        "aud": f"{settings.ISSUER}/userinfo",
        "client_id": client.client_id,
        "scope": ac.scope,
        "acr": ac.acr,
        "iat": now,
        "exp": now + settings.ACCESS_TOKEN_TTL_SEC,
        "jti": new_token(12),
    }
    db.commit()
    return {
        "access_token": sign_jwt(access_claims),
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_TOKEN_TTL_SEC,
        "id_token": sign_jwt(id_claims),
        "scope": ac.scope,
    }


def userinfo_claims(db: Session, access: dict) -> dict:
    user = db.get(User, uuid.UUID(access["sub"]))
    if not user:
        raise OIDCError("invalid_token", "User no longer exists", 401)
    out = {"sub": str(user.id), "acr": access.get("acr")}
    if "profile" in (access.get("scope") or "").split():
        out.update({"name": user.display_name, "preferred_username": user.username})
    return out



# ---------------------------------------------------------------- after sign-in

def next_step(db: Session, auth_req: AuthRequest, sess: AuthSession) -> str:
    """Where to send the browser once the user is signed in at Kavach for this request:
    straight back to the website with a code, or to the consent screen first."""
    client = db.get(OIDCClient, auth_req.client_id)
    if sess.acr == ACR_ASSISTED:
        if not assisted_allowed(client, auth_req):
            raise OIDCError("access_denied", f"{client.name} does not accept assisted sign-in")
        # Owner's OTP + helper approval for this exact website count as consent
        return issue_code(db, auth_req, sess)
    scopes = granted_scopes(client, auth_req.scope)
    if has_consent(db, sess.user_id, client, scopes):
        return issue_code(db, auth_req, sess)
    return f"/consent?req={auth_req.id}"
