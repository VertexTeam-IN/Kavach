"""End-to-end and attack tests. Run live in the demo:  python -m pytest -v"""
from datetime import timedelta

from authlib.jose import JsonWebKey, jwt
from sqlalchemy import update

from app.db import SessionLocal
from app.models import Challenge, utcnow

from .conftest import (
    CITIZEN, COLLEGE, authorize, exchange, latest_otp, login, pkce, query, register,
)
from .soft_authenticator import SoftAuthenticator


def decode_id_token(client, token: str, audience: str) -> dict:
    keys = JsonWebKey.import_key_set(client.get("/.well-known/jwks.json").json())
    claims = jwt.decode(token, keys, claims_options={"aud": {"essential": True, "value": audience}})
    claims.validate()
    return dict(claims)


# ================================================================ passkeys

def test_register_and_login_with_passkey(new_client):
    auth = SoftAuthenticator()
    c = new_client()
    out = register(c, auth, "piyush")
    assert out["recovery_code"].startswith("KVCH-")
    assert c.get("/api/me").json()["username"] == "piyush"

    c2 = new_client()                           # a fresh browser: no cookie
    assert c2.get("/api/me").status_code == 401
    r = login(c2, auth)
    assert r.status_code == 200, r.text
    me = c2.get("/api/me").json()
    assert me["username"] == "piyush" and me["is_assisted"] is False


def test_replayed_login_response_is_rejected(new_client):
    auth = SoftAuthenticator()
    register(new_client(), auth, "piyush")
    c = new_client()
    opts = c.post("/api/webauthn/login/options").json()
    cred = auth.get(opts)
    assert c.post("/api/webauthn/login/verify", json={"credential": cred}).status_code == 200
    replay = c.post("/api/webauthn/login/verify", json={"credential": cred})
    assert replay.status_code == 400


def test_signature_from_lookalike_site_is_rejected(new_client):
    auth = SoftAuthenticator()
    register(new_client(), auth, "piyush")
    c = new_client()
    opts = c.post("/api/webauthn/login/options").json()
    cred = auth.get(opts, origin="https://kavach-login.xyz")
    assert c.post("/api/webauthn/login/verify", json={"credential": cred}).status_code == 400


def test_unknown_passkey_is_rejected(new_client):
    register(new_client(), SoftAuthenticator(), "piyush")
    stranger = SoftAuthenticator()
    c = new_client()
    stranger.create(c.post("/api/webauthn/register/options",
                           json={"username": "ghost", "display_name": "Ghost", "phone": "9999999999"}).json())
    r = login(c, stranger)                       # never verified -> not in database
    assert r.status_code == 400


def test_expired_challenge_is_rejected(new_client):
    auth = SoftAuthenticator()
    register(new_client(), auth, "piyush")
    c = new_client()
    opts = c.post("/api/webauthn/login/options").json()
    with SessionLocal() as db:
        db.execute(update(Challenge).where(Challenge.purpose == "login")
                   .values(expires_at=utcnow() - timedelta(seconds=1)))
        db.commit()
    assert c.post("/api/webauthn/login/verify", json={"credential": auth.get(opts)}).status_code == 400


def test_user_verification_is_required(new_client):
    auth = SoftAuthenticator()
    register(new_client(), auth, "piyush")
    c = new_client()
    opts = c.post("/api/webauthn/login/options").json()
    cred = auth.get(opts, user_verified=False)   # no fingerprint / PIN
    assert c.post("/api/webauthn/login/verify", json={"credential": cred}).status_code == 400


def test_backup_passkey_both_work(new_client):
    laptop, phone = SoftAuthenticator(), SoftAuthenticator()
    c = new_client()
    register(c, laptop, "piyush")
    opts = c.post("/api/webauthn/add/options").json()
    assert c.post("/api/webauthn/add/verify", json={"credential": phone.create(opts)}).status_code == 200
    assert c.get("/api/me").json()["has_backup"] is True
    assert login(new_client(), phone).status_code == 200
    assert login(new_client(), laptop).status_code == 200


# ================================================================ OIDC

def test_oidc_sign_in_to_college_portal(new_client):
    auth = SoftAuthenticator()
    register(new_client(), auth, "piyush")
    c = new_client()
    verifier, challenge = pkce()
    req = query(authorize(c, COLLEGE, challenge))["req"]
    info = c.get(f"/api/oidc/request/{req}").json()
    assert info["client_name"] == "College Portal"

    r = login(c, auth, req=req)
    assert r.json()["next"].startswith("/consent")
    redirect = c.post("/api/oidc/consent", json={"req": req, "allow": True}).json()["redirect"]
    q = query(redirect)
    assert redirect.startswith(COLLEGE["redirect_uri"]) and q["state"] == "st-123"

    tokens = exchange(c, COLLEGE, q["code"], verifier).json()
    claims = decode_id_token(c, tokens["id_token"], COLLEGE["client_id"])
    assert claims["preferred_username"] == "piyush"
    assert claims["nonce"] == "n-456"
    assert claims["acr"] == "urn:kavach:acr:passkey"

    ui = c.get("/userinfo", headers={"Authorization": f"Bearer {tokens['access_token']}"}).json()
    assert ui["preferred_username"] == "piyush"

    # Second visit: already signed in and consented -> straight back with a code
    _, ch2 = pkce()
    loc = authorize(c, COLLEGE, ch2)
    assert loc.startswith(COLLEGE["redirect_uri"]) and "code=" in loc


def test_authorization_code_cannot_be_reused(new_client):
    auth = SoftAuthenticator()
    c = new_client()
    register(c, auth, "piyush")
    verifier, challenge = pkce()
    req = query(authorize(c, COLLEGE, challenge, prompt="login"))["req"]
    login(c, auth, req=req)
    code = query(c.post("/api/oidc/consent", json={"req": req, "allow": True}).json()["redirect"])["code"]
    assert exchange(c, COLLEGE, code, verifier).status_code == 200
    second = exchange(c, COLLEGE, code, verifier)
    assert second.status_code == 400 and second.json()["error"] == "invalid_grant"


def test_wrong_pkce_verifier_is_rejected(new_client):
    auth = SoftAuthenticator()
    c = new_client()
    register(c, auth, "piyush")
    _, challenge = pkce()
    attacker_verifier, _ = pkce()
    req = query(authorize(c, COLLEGE, challenge, prompt="login"))["req"]
    login(c, auth, req=req)
    code = query(c.post("/api/oidc/consent", json={"req": req, "allow": True}).json()["redirect"])["code"]
    r = exchange(c, COLLEGE, code, attacker_verifier)
    assert r.status_code == 400 and r.json()["error"] == "invalid_grant"


def test_unregistered_redirect_uri_is_not_followed(new_client):
    c = new_client()
    _, challenge = pkce()
    r = c.get("/authorize", params={
        "response_type": "code", "client_id": "college-portal", "redirect_uri": "https://attacker.example/steal",
        "scope": "openid", "code_challenge": challenge, "code_challenge_method": "S256"}, follow_redirects=False)
    assert r.status_code == 400 and "attacker" not in r.headers.get("location", "")


def test_wrong_client_secret_is_rejected(new_client):
    c = new_client()
    r = c.post("/token", data={"grant_type": "authorization_code", "code": "x", "client_id": "college-portal",
                               "client_secret": "wrong", "redirect_uri": COLLEGE["redirect_uri"], "code_verifier": "x" * 43})
    assert r.status_code == 401 and r.json()["error"] == "invalid_client"


# ================================================================ assisted access

def _setup_owner_and_helper(new_client):
    owner_auth, helper_auth = SoftAuthenticator(), SoftAuthenticator()
    owner_c, helper_c = new_client(), new_client()
    register(owner_c, owner_auth, "dadi", phone="9000000001")
    register(helper_c, helper_auth, "piyush", phone="9000000002")
    assert owner_c.post("/api/helpers/invite", json={"username": "piyush"}).status_code == 200
    inv = helper_c.get("/api/helpers").json()["invitations"][0]["id"]
    assert helper_c.post(f"/api/helpers/{inv}/accept").status_code == 200
    return helper_c, helper_auth


def _owner_request(new_client, site=COLLEGE):
    c = new_client()                              # the owner on a shared / new device, no passkey
    verifier, challenge = pkce()
    req = query(authorize(c, site, challenge))["req"]
    start = c.post("/api/assist", json={"username": "dadi", "req": req})
    return c, verifier, start


def test_assisted_sign_in_end_to_end(new_client):
    helper_c, helper_auth = _setup_owner_and_helper(new_client)
    c, verifier, start = _owner_request(new_client)
    assert start.status_code == 200, start.text
    s = start.json()
    hdr = {"X-Assist-Token": s["token"]}
    view = c.post(f"/api/assist/{s['id']}/otp", json={"otp": latest_otp(c, s["demo_phone"])}, headers=hdr).json()
    code = view["match_code"]

    hv = helper_c.get(f"/api/assist/{s['id']}/helper").json()
    assert code in hv["choices"] and len(hv["choices"]) == 3
    opts = helper_c.post(f"/api/assist/{s['id']}/approve/options").json()
    r = helper_c.post(f"/api/assist/{s['id']}/approve/verify",
                      json={"credential": helper_auth.get(opts), "chosen": code})
    assert r.status_code == 200, r.text

    done = c.post(f"/api/assist/{s['id']}/complete", headers=hdr)
    assert done.status_code == 200, done.text
    tokens = exchange(c, COLLEGE, query(done.json()["redirect"])["code"], verifier).json()
    claims = decode_id_token(c, tokens["id_token"], COLLEGE["client_id"])
    assert claims["acr"] == "urn:kavach:acr:assisted"
    assert claims["amr"] == ["otp", "helper"]
    assert claims["kavach_assisted_by"] == "Piyush"

    # The approval is single use
    assert c.post(f"/api/assist/{s['id']}/complete", headers=hdr).status_code == 400
    # An assisted session can never manage the account
    assert c.post("/api/webauthn/add/options").status_code == 403
    assert c.post("/api/helpers/invite", json={"username": "piyush"}).status_code == 403


def test_wrong_match_number_twice_cancels(new_client):
    helper_c, helper_auth = _setup_owner_and_helper(new_client)
    c, _, start = _owner_request(new_client)
    s = start.json()
    hdr = {"X-Assist-Token": s["token"]}
    code = c.post(f"/api/assist/{s['id']}/otp", json={"otp": latest_otp(c, s["demo_phone"])}, headers=hdr).json()["match_code"]
    wrong = next(x for x in helper_c.get(f"/api/assist/{s['id']}/helper").json()["choices"] if x != code)
    for _ in range(2):
        opts = helper_c.post(f"/api/assist/{s['id']}/approve/options").json()
        r = helper_c.post(f"/api/assist/{s['id']}/approve/verify",
                          json={"credential": helper_auth.get(opts), "chosen": wrong})
        assert r.status_code == 400
    assert c.get(f"/api/assist/{s['id']}", headers=hdr).json()["status"] == "cancelled"


def test_non_helper_cannot_approve(new_client):
    _setup_owner_and_helper(new_client)
    c, _, start = _owner_request(new_client)
    s = start.json()
    c.post(f"/api/assist/{s['id']}/otp", json={"otp": latest_otp(c, s["demo_phone"])},
           headers={"X-Assist-Token": s["token"]})
    stranger = new_client()
    register(stranger, SoftAuthenticator(), "mallory")
    assert stranger.get(f"/api/assist/{s['id']}/helper").status_code == 403


def test_owner_token_required(new_client):
    _setup_owner_and_helper(new_client)
    c, _, start = _owner_request(new_client)
    s = start.json()
    assert c.get(f"/api/assist/{s['id']}", headers={"X-Assist-Token": "guess"}).status_code == 404


def test_site_that_refuses_assisted_sign_in(new_client):
    _setup_owner_and_helper(new_client)
    _, _, start = _owner_request(new_client, site=CITIZEN)
    assert start.status_code == 400
    assert "does not allow assisted" in start.json()["detail"]


# ================================================================ recovery

def test_recovery_with_code_and_otp(new_client):
    old_laptop = SoftAuthenticator()
    first = register(new_client(), old_laptop, "piyush", phone="9000000009")

    new_laptop = SoftAuthenticator()
    c = new_client()
    s = c.post("/api/recovery/start", json={"username": "piyush", "code": first["recovery_code"]}).json()
    hdr = {"X-Recovery-Token": s["token"]}
    assert c.post(f"/api/recovery/{s['id']}/otp", json={"otp": latest_otp(c, s["demo_phone"])}, headers=hdr).status_code == 200
    opts = c.post(f"/api/recovery/{s['id']}/register/options", headers=hdr).json()
    r = c.post(f"/api/recovery/{s['id']}/register/verify", json={"credential": new_laptop.create(opts)}, headers=hdr)
    assert r.status_code == 200, r.text
    assert r.json()["recovery_code"] != first["recovery_code"]

    assert login(new_client(), new_laptop).status_code == 200   # new key works
    assert login(new_client(), old_laptop).status_code == 400   # lost key revoked
    # used recovery code cannot be reused
    again = new_client().post("/api/recovery/start", json={"username": "piyush", "code": first["recovery_code"]})
    assert again.status_code == 400


def test_wrong_recovery_code(new_client):
    register(new_client(), SoftAuthenticator(), "piyush")
    r = new_client().post("/api/recovery/start", json={"username": "piyush", "code": "KVCH-AAAA-BBBB-CCCC"})
    assert r.status_code == 400
    r2 = new_client().post("/api/recovery/recover", json={"username": "piyush", "code": "KVCH-AAAA-BBBB-CCCC"})
    assert r2.status_code == 400


def test_recovery_with_code_only(new_client):
    laptop = SoftAuthenticator()
    first = register(new_client(), laptop, "aditya")

    c = new_client()
    # Recover directly using only username and recovery code
    res = c.post("/api/recovery/recover", json={"username": "aditya", "code": first["recovery_code"]})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ok"] is True
    assert data["recovery_code"] != first["recovery_code"]
    assert data["recovery_code"].startswith("KVCH-")

    # Session cookie set and valid
    me = c.get("/api/me")
    assert me.status_code == 200
    assert me.json()["username"] == "aditya"

    # Used recovery code cannot be reused
    again = new_client().post("/api/recovery/recover", json={"username": "aditya", "code": first["recovery_code"]})
    assert again.status_code == 400



# ================================================================ client IP / rate limits

def test_spoofed_forwarded_for_does_not_bypass_rate_limit(new_client):
    """A client may not pick its own IP: a fake X-Forwarded-For must not reset the rate limit."""
    import uuid

    c = new_client()
    codes = [
        c.post(f"/api/recovery/{uuid.uuid4()}/otp", json={"otp": "123456"},
               headers={"X-Forwarded-For": f"198.51.100.{i}"}).status_code
        for i in range(1, 13)
    ]
    assert 429 in codes, codes


def test_forwarded_for_is_used_from_a_trusted_proxy(monkeypatch):
    """Behind our own proxy, the real client address (last untrusted hop) is used."""
    from starlette.requests import Request

    from app.config import settings
    from app.security import client_ip

    def req(peer, xff):
        return Request({"type": "http", "client": (peer, 1234), "headers": [(b"x-forwarded-for", xff.encode())]})

    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "127.0.0.1")
    assert client_ip(req("127.0.0.1", "6.6.6.6, 203.0.113.9")) == "203.0.113.9"   # client-added 6.6.6.6 ignored
    assert client_ip(req("10.0.0.5", "203.0.113.9")) == "10.0.0.5"                 # not our proxy: header ignored
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "")
    assert client_ip(req("127.0.0.1", "203.0.113.9")) == "127.0.0.1"               # default: trust no one


# ================================================================ alerts, sessions, passkey health, score

def _alerts(c):
    return c.get("/api/alerts").json()


def test_new_device_sign_in_alert_and_this_wasnt_me(new_client):
    auth = SoftAuthenticator()
    owner = new_client()
    register(owner, auth, "piyush")
    assert _alerts(owner)["items"] == []                      # registering is not an alert

    thief = new_client()
    thief.headers["user-agent"] = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0"
    assert login(thief, auth).status_code == 200
    a = _alerts(owner)
    assert a["open_warnings"] == 1 and a["items"][0]["kind"] == "login_success"
    assert "Chrome on Linux" in a["items"][0]["detail"] and a["items"][0]["can_report"]

    same = new_client()                                        # same browser as before: no new alert
    assert login(same, auth).status_code == 200
    assert _alerts(owner)["open_warnings"] == 1

    r = owner.post(f"/api/alerts/{a['items'][0]['id']}/not-me")
    assert r.status_code == 200 and r.json()["done"][0].startswith("Signed out 2")
    assert thief.get("/api/me").status_code == 401 and same.get("/api/me").status_code == 401
    assert owner.get("/api/me").status_code == 200            # the owner's own session stays
    assert _alerts(owner)["open_warnings"] == 0
    assert owner.post(f"/api/alerts/{a['items'][0]['id']}/not-me").status_code == 400   # only once


def test_passkey_added_alert_not_me_removes_that_passkey(new_client):
    laptop, rogue = SoftAuthenticator(), SoftAuthenticator()
    c = new_client()
    register(c, laptop, "piyush")
    opts = c.post("/api/webauthn/add/options").json()
    assert c.post("/api/webauthn/add/verify", json={"credential": rogue.create(opts)}).status_code == 200
    alert = next(i for i in _alerts(c)["items"] if i["kind"] == "passkey_added")
    assert c.post(f"/api/alerts/{alert['id']}/not-me").json()["done"][1] == "Removed the new passkey"
    assert len(c.get("/api/passkeys").json()) == 1
    assert login(new_client(), rogue).status_code == 400     # the rogue passkey no longer works


def test_sign_out_all_other_sessions(new_client):
    auth = SoftAuthenticator()
    a = new_client()
    register(a, auth, "piyush")
    b, d = new_client(), new_client()
    login(b, auth), login(d, auth)
    r = a.post("/api/sessions/revoke-others")
    assert r.status_code == 200 and r.json()["signed_out"] == 2
    assert b.get("/api/me").status_code == 401 and d.get("/api/me").status_code == 401
    assert a.get("/api/me").status_code == 200


def test_passkey_model_and_health_fields(new_client):
    c = new_client()
    register(c, SoftAuthenticator(), "piyush")
    p = c.get("/api/passkeys").json()[0]
    assert p["model"] == "Built into this device" and p["stale"] is False


def test_security_score(new_client):
    laptop, phone = SoftAuthenticator(), SoftAuthenticator()
    c = new_client()
    register(c, laptop, "piyush")
    s = c.get("/api/security-score").json()
    assert s["score"] == 55 and s["level"] == "weak"          # recovery code + no stale + no alerts
    opts = c.post("/api/webauthn/add/options").json()
    c.post("/api/webauthn/add/verify", json={"credential": phone.create(opts)})
    assert c.get("/api/security-score").json()["score"] == 70  # +30 backup, -15 unreviewed alert
    alert = next(i for i in _alerts(c)["items"] if i["kind"] == "passkey_added")
    assert c.post(f"/api/alerts/{alert['id']}/me").status_code == 200
    assert c.get("/api/security-score").json() | {"checks": None} == {"score": 85, "level": "strong", "checks": None}


def test_assisted_session_cannot_use_alert_actions(new_client):
    helper_c, helper_auth = _setup_owner_and_helper(new_client)
    c, verifier, start = _owner_request(new_client)
    s = start.json()
    hdr = {"X-Assist-Token": s["token"]}
    code = c.post(f"/api/assist/{s['id']}/otp", json={"otp": latest_otp(c, s["demo_phone"])}, headers=hdr).json()["match_code"]
    opts = helper_c.post(f"/api/assist/{s['id']}/approve/options").json()
    helper_c.post(f"/api/assist/{s['id']}/approve/verify", json={"credential": helper_auth.get(opts), "chosen": code})
    assert c.post(f"/api/assist/{s['id']}/complete", headers=hdr).status_code == 200
    a = _alerts(c)                                              # the owner can SEE alerts in view-only mode…
    alert = next(i for i in a["items"] if i["kind"] == "assist_login")
    assert "Piyush" in alert["detail"]
    assert c.post(f"/api/alerts/{alert['id']}/not-me").status_code == 403   # …but not act on them
    assert c.post("/api/sessions/revoke-others").status_code == 403
