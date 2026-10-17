"""Kavach's own RSA signing key (RS256) for ID tokens and access tokens.

The private key is created once and saved to keys/kavach_private.pem (gitignored),
so tokens stay valid across server restarts. The public half is published at
/.well-known/jwks.json for websites to verify tokens.
"""
from pathlib import Path

from authlib.jose import JsonWebKey, jwt

from .config import settings

_key = None
_kid: str | None = None


def get_key():
    global _key, _kid
    if _key is not None:
        return _key
    path = Path(settings.KEY_PATH)
    if path.exists():
        _key = JsonWebKey.import_key(path.read_bytes(), {"kty": "RSA"})
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        _key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
        pem = _key.as_pem(is_private=True)
        path.write_bytes(pem if isinstance(pem, bytes) else pem.encode())
    _kid = _key.thumbprint()
    return _key


def get_kid() -> str:
    get_key()
    assert _kid is not None
    return _kid


def jwks() -> dict:
    key = get_key()
    pub = key.as_dict(is_private=False)
    pub.update({"kid": get_kid(), "use": "sig", "alg": "RS256"})
    return {"keys": [pub]}


def sign_jwt(claims: dict) -> str:
    token = jwt.encode({"alg": "RS256", "kid": get_kid(), "typ": "JWT"}, claims, get_key())
    return token.decode() if isinstance(token, bytes) else token


def verify_jwt(token: str, audience: str | None = None) -> dict:
    """Verify signature + exp (+ iss, optional aud). Raises on any problem."""
    options = {"iss": {"essential": True, "value": settings.ISSUER}}
    if audience:
        options["aud"] = {"essential": True, "value": audience}
    claims = jwt.decode(token, get_key(), claims_options=options)
    claims.validate()
    return dict(claims)
