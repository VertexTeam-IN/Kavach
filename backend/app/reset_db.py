"""Wipe and recreate the database, then re-seed demo websites.

    python -m app.reset_db

Run this between demo rehearsals. Also delete old 'localhost' passkeys in
Windows Settings -> Accounts -> Passkeys, otherwise Windows keeps offering accounts
that no longer exist in the database.
"""
from .db import Base, SessionLocal, engine
from .seed import seed_clients


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        n = seed_clients(db)
    print(f"Database reset. {n} demo website(s) seeded.")


if __name__ == "__main__":
    main()
