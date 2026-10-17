"""OpenID Connect provider endpoints — what websites integrate with."""
import html

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import Ctx, current
from ..keys import jwks, verify_jwt
from ..models import OIDCClient, utcnow
from ..schemas import ConsentBody, ContinueBody
from ..security import client_ip, rate_limit
from ..services import audit_service, oidc_service
from ..services.oidc_service import OIDCError, RedirectableError
from ..services.session_service import ACR_PASSKEY, find_session, logout as end_session

router = APIRouter(tags=["oidc"])

SCOPE_LABELS = {"openid": "Your Kavach ID", "profile": "Your name and username"}


def _abs(url: str) -> str:
    return f"{settings.ISSUER}{url}" if url.startswith("/") else url


def _error_page(title: str, message: str, status: int = 400) -> HTMLResponse:
    body = f"""<!doctype html><html><head><meta charset="utf-8"><title>Kavach — {html.escape(title)}</title>
<style>body{{font-family:system-ui,sans-serif;background:#0F1B2D;color:#fff;display:grid;place-items:center;height:100vh;margin:0}}
.c{{max-width:480px;padding:32px;background:#16263d;border-radius:16px}}h1{{color:#F2A93B;font-size:22px}}</style></head>
<body><div class="c"><h1>{html.escape(title)}</h1><p>{html.escape(message)}</p>
<p>Go back to the website and try signing in again.</p></div></body></html>"""
    return HTMLResponse(body, status_code=status)


# ---------------------------------------------------------------- discovery

@router.get("/.well-known/openid-configuration")
def openid_configuration():
    return oidc_service.discovery()


@router.get("/.well-known/jwks.json")
def jwks_endpoint():
    return jwks()


# ---------------------------------------------------------------- authorize

@router.get("/authorize")
def authorize(request: Request, db: Session = Depends(get_db)):
    params = dict(request.query_params)
    try:
        auth_req = oidc_service.start_authorization(db, params)
    except RedirectableError as e:
        return RedirectResponse(oidc_service.error_redirect(e.auth_req, e.error, e.description), status_code=302)
    except OIDCError as e:
        return _error_page("Sign-in request rejected", e.description)

    audit_service.log(db, "authorize_started", client_id=auth_req.client_id, ip=client_ip(request), commit=True)

    sess = find_session(db, request)
    if sess and auth_req.prompt != "login":
        if sess.acr == ACR_PASSKEY:
            url = oidc_service.next_step(db, auth_req, sess)
            db.commit()
            return RedirectResponse(_abs(url), status_code=302)
    if auth_req.prompt == "none":
        url = oidc_service.error_redirect(auth_req, "login_required", "User is not signed in")
        auth_req.completed_at = utcnow()
        db.commit()
        return RedirectResponse(url, status_code=302)
    return RedirectResponse(f"{settings.ISSUER}/login?req={auth_req.id}", status_code=302)


@router.get("/api/oidc/request/{req}")
def request_info(req: str, db: Session = Depends(get_db)):
    """Used by the login / consent pages to show which website is asking."""
    auth_req = oidc_service.load_auth_request(db, req)
    client = db.get(OIDCClient, auth_req.client_id)
    scopes = oidc_service.granted_scopes(client, auth_req.scope)
    return {
        "req": str(auth_req.id),
        "client_id": client.client_id,
        "client_name": client.name,
        "scopes": [SCOPE_LABELS.get(s, s) for s in scopes],
        "allow_assisted": oidc_service.assisted_allowed(client, auth_req),
        "expires_at": auth_req.expires_at.isoformat(),
    }


@router.post("/api/oidc/continue")
def continue_sign_in(body: ContinueBody, ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    """Already signed in at Kavach: continue a website's sign-in request."""
    auth_req = oidc_service.load_auth_request(db, body.req)
    url = oidc_service.next_step(db, auth_req, ctx.session)
    db.commit()
    return {"redirect": url}


@router.post("/api/oidc/consent")
def consent(body: ConsentBody, request: Request, ctx: Ctx = Depends(current), db: Session = Depends(get_db)):
    auth_req = oidc_service.load_auth_request(db, body.req)
    client = db.get(OIDCClient, auth_req.client_id)
    if not body.allow:
        auth_req.completed_at = utcnow()
        audit_service.log(db, "consent_denied", actor_id=ctx.user.id, client_id=client.client_id, ip=client_ip(request))
        db.commit()
        return {"redirect": oidc_service.error_redirect(auth_req, "access_denied", "User denied access")}
    oidc_service.save_consent(db, ctx.user.id, client, oidc_service.granted_scopes(client, auth_req.scope))
    url = oidc_service.issue_code(db, auth_req, ctx.session)
    audit_service.log(db, "consent_granted", actor_id=ctx.user.id, client_id=client.client_id, ip=client_ip(request))
    db.commit()
    return {"redirect": url}


# ---------------------------------------------------------------- token / userinfo

def _oauth_error(e: OIDCError) -> JSONResponse:
    return JSONResponse({"error": e.error, "error_description": e.description}, status_code=e.status,
                        headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


@router.post("/token")
async def token(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    rate_limit(request, "token", limit=60, window_sec=60)
    form = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
    try:
        client = oidc_service.authenticate_client(db, form, authorization)
        tokens = oidc_service.exchange_code(db, client, form)
    except OIDCError as e:
        audit_service.log(db, "token_rejected", client_id=form.get("client_id"), ip=client_ip(request),
                          reason=e.error, commit=True)
        return _oauth_error(e)
    audit_service.log(db, "token_issued", client_id=client.client_id, ip=client_ip(request), commit=True)
    return JSONResponse(tokens, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


@router.api_route("/userinfo", methods=["GET", "POST"])
def userinfo(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        return JSONResponse({"error": "invalid_token"}, status_code=401,
                            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    try:
        access = verify_jwt(authorization[7:].strip(), audience=f"{settings.ISSUER}/userinfo")
        return oidc_service.userinfo_claims(db, access)
    except OIDCError as e:
        return _oauth_error(e)
    except Exception:
        return JSONResponse({"error": "invalid_token"}, status_code=401,
                            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})


# ---------------------------------------------------------------- logout

@router.get("/logout")
def rp_logout(request: Request, post_logout_redirect_uri: str | None = None, client_id: str | None = None,
              state: str | None = None, db: Session = Depends(get_db)):
    target = f"{settings.ISSUER}/"
    if post_logout_redirect_uri:
        clients = [db.get(OIDCClient, client_id)] if client_id else list(db.query(OIDCClient).all())
        if any(c and post_logout_redirect_uri in (c.post_logout_redirect_uris or []) for c in clients):
            target = oidc_service.add_query(post_logout_redirect_uri, {"state": state})
    resp = RedirectResponse(target, status_code=302)
    end_session(db, request, resp)
    db.commit()
    return resp
