"""Register a new website (OIDC client) with Kavach.

    python -m app.cli register-client --name "My College" --redirect-uri http://127.0.0.1:4000/callback
    python -m app.cli list-clients

Prints the client_id and client_secret ONCE — paste them into the website's OIDC settings.
"""
import argparse
import re
import secrets

from .config import settings
from .db import Base, SessionLocal, engine
from .models import OIDCClient
from .security import argon2_hash


def register(args) -> None:
    client_id = args.client_id or re.sub(r"[^a-z0-9]+", "-", args.name.lower()).strip("-")
    secret = None if args.public else secrets.token_urlsafe(32)
    with SessionLocal() as db:
        if db.get(OIDCClient, client_id):
            raise SystemExit(f"Client '{client_id}' already exists")
        db.add(OIDCClient(
            client_id=client_id,
            name=args.name,
            secret_hash=argon2_hash(secret) if secret else None,
            redirect_uris=args.redirect_uri,
            post_logout_redirect_uris=args.post_logout_uri or [],
            scopes=["openid", "profile"],
            allow_assisted=not args.no_assisted,
            is_public=args.public,
        ))
        db.commit()
    print("Website registered with Kavach")
    print(f"  issuer        : {settings.ISSUER}")
    print(f"  client_id     : {client_id}")
    print(f"  client_secret : {secret or '(public client — use PKCE, no secret)'}")
    print(f"  redirect_uris : {', '.join(args.redirect_uri)}")


def list_clients(_args) -> None:
    with SessionLocal() as db:
        for c in db.query(OIDCClient).all():
            print(f"{c.client_id:20} {c.name:30} assisted={'yes' if c.allow_assisted else 'no '}  {c.redirect_uris}")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    p = argparse.ArgumentParser(prog="python -m app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register-client")
    r.add_argument("--name", required=True)
    r.add_argument("--client-id")
    r.add_argument("--redirect-uri", action="append", required=True)
    r.add_argument("--post-logout-uri", action="append")
    r.add_argument("--public", action="store_true", help="SPA/mobile client without a secret")
    r.add_argument("--no-assisted", action="store_true", help="Refuse assisted sign-ins for this website")
    r.set_defaults(func=register)
    ls = sub.add_parser("list-clients")
    ls.set_defaults(func=list_clients)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
