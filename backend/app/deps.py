"""FastAPI dependencies for the current login."""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import AuthSession, User
from .services.session_service import ACR_PASSKEY, find_session


@dataclass
class Ctx:
    session: AuthSession
    user: User

    @property
    def is_assisted(self) -> bool:
        return self.session.acr != ACR_PASSKEY


def current(request: Request, db: Session = Depends(get_db)) -> Ctx:
    """Any valid session (passkey or assisted)."""
    sess = find_session(db, request)
    if not sess:
        raise HTTPException(status_code=401, detail="Not signed in")
    user = db.get(User, sess.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    return Ctx(session=sess, user=user)


def full_login(ctx: Ctx = Depends(current)) -> Ctx:
    """Only a real passkey session. Assisted sessions can never manage passkeys, helpers,
    recovery or sessions."""
    if ctx.is_assisted:
        raise HTTPException(status_code=403, detail="Not allowed in an assisted session. Sign in with your own passkey.")
    return ctx
