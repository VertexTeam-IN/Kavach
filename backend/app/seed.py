"""Load demo websites (OIDC clients) from seed_clients.json into the database."""
import json
from pathlib import Path

from sqlalchemy.orm import Session

from .config import settings
from .models import OIDCClient
from .security import argon2_hash, argon2_verify


def seed_clients(db: Session, path: str | None = None) -> int:
    file = Path(path or settings.SEED_CLIENTS_PATH)
    if not file.exists():
        return 0
    count = 0
    for c in json.loads(file.read_text(encoding="utf-8")):
        client = db.get(OIDCClient, c["client_id"])
        if client is None:
            client = OIDCClient(client_id=c["client_id"])
            db.add(client)
        client.name = c["name"]
        client.redirect_uris = c["redirect_uris"]
        client.post_logout_redirect_uris = c.get("post_logout_redirect_uris", [])
        client.scopes = c.get("scopes", ["openid", "profile"])
        client.allow_assisted = c.get("allow_assisted", True)
        client.is_public = c.get("is_public", False)
        secret = c.get("client_secret")
        if secret and not argon2_verify(client.secret_hash, secret):
            client.secret_hash = argon2_hash(secret)
        count += 1
    db.commit()
    return count
