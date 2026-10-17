"""Small security helpers: random tokens, hashing, OTPs, cookies, rate limiting."""
import base64
import hashlib
import hmac
import random
import secrets
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request, Response

from .config import settings

_ph = PasswordHasher()


# ---------- random values ----------

def new_token(nbytes: int = 32) -> str:
    """URL-safe random token (session ids, auth codes, assist tokens)."""
    return secrets.token_urlsafe(nbytes)


def new_otp() -> str:
    """6-digit one-time code."""
    return f"{secrets.randbelow(10**6):06d}"


def new_match_code_and_choices() -> tuple[str, list[str]]:
    """2-digit number the owner reads out + 3 shuffled choices shown to the helper."""
    correct = secrets.randbelow(90) + 10
    decoys: set[int] = set()
    while len(decoys) < 2:
        d = secrets.randbelow(90) + 10
        if d != correct:
            decoys.add(d)
    choices = [str(correct)] + [str(d) for d in decoys]
    random.SystemRandom().shuffle(choices)
    return str(correct), choices


def new_recovery_code() -> str:
    """Human-friendly recovery code, e.g. KVCH-7Q2M-9XPL-4RTA (no 0/O/1/I)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return "KVCH-" + "-".join(groups)


# ---------- hashing ----------

def sha256_hex(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def constant_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def argon2_hash(secret: str) -> str:
    return _ph.hash(secret)


def argon2_verify(hash_: str | None, secret: str) -> bool:
    if not hash_:
        return False
    try:
        return _ph.verify(hash_, secret)
    except (VerificationError, InvalidHashError):
        return False


def normalize_recovery_code(code: str) -> str:
    return code.strip().upper().replace(" ", "")


# ---------- base64url ----------

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


# ---------- cookies ----------

def set_session_cookie(response: Response, token: str, max_age_sec: int) -> None:
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=max_age_sec,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")


# ---------- rate limiting (in-memory, per process — fine for a single demo server) ----------

_hits: dict[str, deque] = defaultdict(deque)


def _trusted_proxies() -> set[str]:
    return {p.strip() for p in settings.TRUSTED_PROXIES.split(",") if p.strip()}


def client_ip(request: Request) -> str:
    """The caller's IP, used for rate limits and the audit log.

    X-Forwarded-For is client-controlled, so it is only believed when the request comes from one
    of our own proxies (settings.TRUSTED_PROXIES). Each proxy appends the address it saw, so we
    read the list right-to-left and take the first hop that is not one of ours.
    """
    peer = request.client.host if request.client else "unknown"
    trusted = _trusted_proxies()
    if peer not in trusted:
        return peer
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    for hop in reversed(hops):
        if hop not in trusted:
            return hop
    return peer


def rate_limit(request: Request, bucket: str, limit: int, window_sec: int) -> None:
    """Raise 429 if this IP hit `bucket` more than `limit` times in `window_sec`."""
    key = f"{bucket}:{client_ip(request)}"
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window_sec:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="Too many attempts. Please wait a minute and try again.")
    q.append(now)


def reset_rate_limits() -> None:
    _hits.clear()
