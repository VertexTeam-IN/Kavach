"""Each attack sends a real request to the running Kavach and records what came back.

An attack returns:
    { outcome: "blocked" | "allowed", verdict: str,
      steps: [ {title, who, kind, call, status, body, note} ] }
A "legit" function runs the same flow WITHOUT the tampering, and should end "allowed".

`who` is the actor taking the step (victim / helper / attacker / website / kavach) and `call`
is the HTTP request that step sent — the UI plays the steps back one by one using these.

The card metadata (title, what the attacker does, plain-language explanation, threat-model row,
matching test name) lives in REGISTRY at the bottom.
"""
import base64
import json
import secrets
import threading
import time

import kavach_client as K
from soft_authenticator import SoftAuthenticator

# Scenario actors are created once per lab boot (fresh usernames avoid clashes with old runs).
SUFFIX = secrets.token_hex(2)


class Scenario:
    def __init__(self):
        self.ready = False
        self.error = None
        self.victim = None      # (auth, username, recovery_code, phone)
        self.helper = None
        self.attacker = None
        self._lock = threading.Lock()

    def setup(self):
        if self.ready:
            return
        # Endpoints run in a thread pool, and React dev mode fetches /scenario twice on load —
        # without the lock two requests could each register their own set of demo users.
        with self._lock:
            if not self.ready:
                self._setup()

    def _setup(self):
        if not K.health():
            self.error = "Kavach backend is not reachable on http://127.0.0.1:8000. Start Kavach first."
            raise K.KavachDown(self.error)
        v_auth, h_auth, a_auth = SoftAuthenticator(), SoftAuthenticator(), SoftAuthenticator()
        v_name, h_name, a_name = f"lab_victim_{SUFFIX}", f"lab_helper_{SUFFIX}", f"lab_attacker_{SUFFIX}"
        v_phone = f"90000{secrets.randbelow(90000)+10000}"

        with K.client() as c:
            reg = K.register(c, v_auth, v_name, "Demo Victim", v_phone)
        with K.client() as c:
            K.register(c, h_auth, h_name, "Demo Helper", "9000000002")
        with K.client() as c:
            K.register(c, a_auth, a_name, "Demo Attacker", "9000000003")

        # victim invites helper; helper accepts  (both need a passkey session)
        vc = K.logged_in_client(v_auth)
        vc.post("/api/helpers/invite", json={"username": h_name})
        hc = K.logged_in_client(h_auth)
        invs = hc.get("/api/helpers").json().get("invitations", [])
        if invs:
            hc.post(f"/api/helpers/{invs[0]['id']}/accept")
        vc.close(); hc.close()

        self.victim = (v_auth, v_name, reg.get("recovery_code"), v_phone)
        self.helper = (h_auth, h_name)
        self.attacker = (a_auth, a_name)
        self.ready = True

    def status(self):
        return {
            "ready": self.ready,
            "error": self.error,
            "victim": self.victim[1] if self.victim else None,
            "helper": self.helper[1] if self.helper else None,
            "attacker": self.attacker[1] if self.attacker else None,
        }


SCN = Scenario()


# ---------------------------------------------------------------- redaction + step builders

SECRET_KEYS = {
    "challenge", "signature", "clientdatajson", "attestationobject", "authenticatordata",
    "publickey", "public_key", "credentialpublickey", "code", "code_verifier", "client_secret",
    "otp", "recovery_code", "token", "rawid", "id", "userhandle",
}


def redact(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k.lower() in SECRET_KEYS and isinstance(v, (str, bytes)):
                out[k] = "«redacted»"
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    if isinstance(obj, str) and len(obj) > 80:
        return obj[:24] + "…«truncated»"
    return obj


def body_of(resp):
    try:
        return redact(resp.json())
    except Exception:
        t = resp.text
        return (t[:200] + "…") if len(t) > 200 else t


def step(title, *, who="kavach", kind="info", req=None, resp=None, note=""):
    s = {"title": title, "who": who, "kind": kind, "note": note}
    if req is not None:
        s["request"] = redact(req)
    if resp is not None:
        s["call"] = f"{resp.request.method} {resp.request.url.path}"
        s["status"] = resp.status_code
        s["body"] = body_of(resp)
    return s


def result(outcome, verdict, steps):
    return {"outcome": outcome, "verdict": verdict, "steps": steps}


# ================================================================ OIDC attacks

def reuse_auth_code(_legit=False):
    v = SCN.victim[0]
    verifier, challenge = K.pkce()
    c, code = K.get_authorization_code(v, K.COLLEGE, verifier, challenge)
    steps = [step("Obtain a real authorization code via a legitimate sign-in", who="victim", kind="ok",
                  note="A valid 60-second, single-use code was issued to the registered redirect URI.")]
    first = K.exchange(c, K.COLLEGE, code, verifier)
    steps.append(step("Exchange the code at /token (first time)", who="website", kind="ok", resp=first,
                      note="Succeeds — tokens issued."))
    c.close()
    if _legit:
        return result("allowed", "A code used exactly once is accepted — normal sign-in works.", steps)
    c2 = K.client()
    second = K.exchange(c2, K.COLLEGE, code, verifier)
    c2.close()
    blocked = second.status_code == 400
    steps.append(step("Replay the SAME code at /token", who="attacker", kind="blocked" if blocked else "warn",
                      resp=second, note="Rejected — the code was already consumed."))
    return result("blocked" if blocked else "allowed",
                  "Authorization codes are single-use. The replay returns invalid_grant.", steps)


def wrong_pkce(_legit=False):
    v = SCN.victim[0]
    verifier, challenge = K.pkce()
    c, code = K.get_authorization_code(v, K.COLLEGE, verifier, challenge)
    steps = [step("Obtain a real authorization code (bound to a PKCE challenge)", who="victim", kind="ok",
                  note="The website kept the secret code_verifier; only its hash went to Kavach.")]
    if _legit:
        r = K.exchange(c, K.COLLEGE, code, verifier)
        c.close()
        ok = r.status_code == 200
        steps.append(step("Exchange with the CORRECT code_verifier", who="website", kind="ok" if ok else "warn", resp=r))
        return result("allowed" if ok else "blocked", "The matching verifier is accepted.", steps)
    attacker_verifier = secrets.token_urlsafe(48)
    r = K.exchange(c, K.COLLEGE, code, attacker_verifier)
    c.close()
    blocked = r.status_code == 400
    steps.append(step("Exchange the stolen code with a WRONG code_verifier", who="attacker",
                      kind="blocked" if blocked else "warn", resp=r,
                      note="Rejected — PKCE binds the code to the verifier only the real client holds."))
    return result("blocked" if blocked else "allowed",
                  "PKCE (S256) is verified before any token is issued — invalid_grant.", steps)


def unregistered_redirect(_legit=False):
    verifier, challenge = K.pkce()
    with K.client() as c:
        if _legit:
            r = c.get("/authorize", params={
                "response_type": "code", "client_id": "college-portal",
                "redirect_uri": K.COLLEGE["redirect_uri"], "scope": "openid profile",
                "code_challenge": challenge, "code_challenge_method": "S256"}, follow_redirects=False)
            ok = r.status_code in (302, 303) and "attacker" not in r.headers.get("location", "")
            return result("allowed" if ok else "blocked",
                          "A registered redirect URI is accepted and the flow proceeds.",
                          [step("Request /authorize with the REGISTERED redirect URI", who="website",
                                kind="ok" if ok else "warn",
                                note=f"Server responds {r.status_code} and continues to sign-in.")])
        evil = "https://attacker.example/steal"
        r = c.get("/authorize", params={
            "response_type": "code", "client_id": "college-portal", "redirect_uri": evil,
            "scope": "openid profile", "code_challenge": challenge,
            "code_challenge_method": "S256"}, follow_redirects=False)
    loc = r.headers.get("location", "")
    blocked = r.status_code == 400 and "attacker" not in loc
    return result("blocked" if blocked else "allowed",
                  "An unregistered redirect URI is refused with an error page — no code is ever sent there.",
                  [step("Request /authorize with redirect_uri = attacker.example", who="attacker",
                        kind="blocked" if blocked else "warn", resp=r,
                        note="Server shows an error page and does NOT redirect to the attacker.")])


def wrong_client_secret(_legit=False):
    secret = K.COLLEGE["secret"] if _legit else "totally-wrong-secret"
    with K.client() as c:
        r = c.post("/token", data={
            "grant_type": "authorization_code", "code": "any-code-here",
            "redirect_uri": K.COLLEGE["redirect_uri"], "client_id": "college-portal",
            "client_secret": secret, "code_verifier": "x" * 43})
    if _legit:
        # correct secret passes client auth; the dummy code then fails as invalid_grant (expected)
        ok = r.status_code == 400 and r.json().get("error") == "invalid_grant"
        return result("allowed" if ok else "blocked",
                      "With the correct secret, client authentication passes (the dummy code then fails as invalid_grant, which is expected).",
                      [step("Call /token with the CORRECT client secret", who="website", kind="ok" if ok else "warn", resp=r)])
    blocked = r.status_code == 401 and r.json().get("error") == "invalid_client"
    return result("blocked" if blocked else "allowed",
                  "A wrong client secret fails client authentication before the code is even looked at — invalid_client.",
                  [step("Call /token pretending to be college-portal, with a WRONG secret", who="attacker",
                        kind="blocked" if blocked else "warn", resp=r)])


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _jwt_parts(token: str):
    head, payload, sig = token.split(".")
    pad = lambda s: s + "=" * (-len(s) % 4)
    return (json.loads(base64.urlsafe_b64decode(pad(head))),
            json.loads(base64.urlsafe_b64decode(pad(payload))), sig)


def _access_token_for(auth):
    verifier, challenge = K.pkce()
    c, code = K.get_authorization_code(auth, K.COLLEGE, verifier, challenge)
    tok = K.exchange(c, K.COLLEGE, code, verifier).json()["access_token"]
    c.close()
    return tok


def forged_access_token(_legit=False):
    def userinfo(tok):
        with K.client() as c:
            return c.get("/userinfo", headers={"Authorization": f"Bearer {tok}"})

    if _legit:
        tok = _access_token_for(SCN.victim[0])
        r = userinfo(tok)
        ok = r.status_code == 200
        return result("allowed" if ok else "blocked",
                      "A real, untouched access token signed by Kavach returns the user's profile.",
                      [step("Victim signs in to the College Portal and gets an access token", who="victim", kind="ok"),
                       step("Website calls /userinfo with that token", who="website", kind="ok" if ok else "warn", resp=r)])

    steps = []
    victim_sub = userinfo(_access_token_for(SCN.victim[0])).json().get("sub")
    steps.append(step("Victim's user id leaks (it is printed inside every ID token)", who="victim", kind="info",
                      note=f"sub = {victim_sub}"))

    own = _access_token_for(SCN.attacker[0])
    r_own = userinfo(own)
    steps.append(step("Attacker signs in with their OWN passkey and gets a genuine token", who="attacker",
                      kind="ok", resp=r_own, note="Works — but it only shows the attacker's own profile."))

    head, payload, sig = _jwt_parts(own)
    payload["sub"] = victim_sub
    edited = f"{_b64url(json.dumps(head).encode())}.{_b64url(json.dumps(payload).encode())}.{sig}"
    r_edit = userinfo(edited)
    edit_blocked = r_edit.status_code == 401
    steps.append(step("Edit the token: swap 'sub' to the victim's id, keep the old signature", who="attacker",
                      kind="blocked" if edit_blocked else "warn", resp=r_edit,
                      note="Rejected — the RS256 signature no longer matches the edited payload."))

    none_head = {"alg": "none", "typ": "JWT"}
    unsigned = f"{_b64url(json.dumps(none_head).encode())}.{_b64url(json.dumps(payload).encode())}."
    r_none = userinfo(unsigned)
    none_blocked = r_none.status_code == 401
    steps.append(step("Try the classic trick: alg = 'none' and no signature at all", who="attacker",
                      kind="blocked" if none_blocked else "warn", resp=r_none,
                      note="Rejected — Kavach only accepts tokens signed with its own private key."))

    blocked = edit_blocked and none_blocked
    return result("blocked" if blocked else "allowed",
                  "Tokens are signed by Kavach (RS256). Changing any byte, or stripping the signature, makes the token invalid — "
                  "so an attacker cannot turn their own token into the victim's.", steps)


# ================================================================ passkey attacks

def replay_login(_legit=False):
    v = SCN.victim[0]
    c = K.client()
    opts = K.login_options(c)
    cred = v.get(opts)
    first = c.post("/api/webauthn/login/verify", json={"credential": cred})
    steps = [step("Victim signs in once with a real passkey assertion", who="victim", kind="ok", resp=first,
                  note="Succeeds — a fresh challenge was signed.")]
    if _legit:
        c.close()
        return result("allowed", "A passkey assertion signing a fresh challenge is accepted.", steps)
    c2 = K.client()
    second = c2.post("/api/webauthn/login/verify", json={"credential": cred})
    c.close(); c2.close()
    blocked = second.status_code == 400
    steps.append(step("Capture that exact assertion and REPLAY it", who="attacker", kind="blocked" if blocked else "warn",
                      resp=second, note="Rejected — the one-time challenge was already consumed."))
    return result("blocked" if blocked else "allowed",
                  "Each login uses a fresh, single-use challenge. A replayed assertion is rejected.", steps)


def lookalike_origin(_legit=False):
    v = SCN.victim[0]
    c = K.client()
    opts = K.login_options(c)
    origin = K.ORIGIN if _legit else "https://kavach-login.xyz"
    cred = v.get(opts, origin=origin)   # a VALID signature, but over the wrong origin
    r = c.post("/api/webauthn/login/verify", json={"credential": cred})
    c.close()
    if _legit:
        ok = r.status_code == 200
        return result("allowed" if ok else "blocked",
                      "A signature made for the real origin (http://localhost:3000) is accepted.",
                      [step("Sign in with the correct origin in clientDataJSON", who="victim", kind="ok" if ok else "warn", resp=r)])
    blocked = r.status_code == 400
    return result("blocked" if blocked else "allowed",
                  "The assertion is validly signed, yet rejected because its origin is a look-alike site, not Kavach. "
                  "This is origin binding. (For the browser-enforced version, open http://127.0.0.1:3000/login — the "
                  "browser itself refuses to offer the passkey.)",
                  [step("Victim is tricked into signing on kavach-login.xyz", who="victim", kind="info",
                        note="The phishing page relays Kavach's challenge to the victim's passkey."),
                   step("Forward that signature to the real Kavach", who="attacker",
                        kind="blocked" if blocked else "warn", resp=r,
                        note="Simulated origin mismatch — rejected on the origin check.")])


def no_user_verification(_legit=False):
    v = SCN.victim[0]
    c = K.client()
    opts = K.login_options(c)
    cred = v.get(opts, user_verified=_legit)   # legit: UV on; attack: UV off (no PIN/biometric)
    r = c.post("/api/webauthn/login/verify", json={"credential": cred})
    c.close()
    if _legit:
        ok = r.status_code == 200
        return result("allowed" if ok else "blocked",
                      "With user verification (fingerprint/face/PIN) present, the login is accepted.",
                      [step("Sign in with user-verification flag set", who="victim", kind="ok" if ok else "warn", resp=r)])
    blocked = r.status_code == 400
    return result("blocked" if blocked else "allowed",
                  "Kavach requires user verification. An assertion made without the fingerprint/face/PIN step is rejected.",
                  [step("Use the victim's unlocked device without the PIN/fingerprint step", who="attacker",
                        kind="blocked" if blocked else "warn", resp=r)])


def unknown_credential(_legit=False):
    if _legit:
        v = SCN.victim[0]
        r = K.login(K.client(), v)
        ok = r.status_code == 200
        return result("allowed" if ok else "blocked",
                      "A passkey that is actually registered signs in.",
                      [step("Sign in with a REGISTERED passkey", who="victim", kind="ok" if ok else "warn", resp=r)])
    ghost = SoftAuthenticator()
    c = K.client()
    # make a credential but never register it with the server
    opts = c.post("/api/webauthn/register/options",
                  json={"username": f"ghost_{secrets.token_hex(2)}", "display_name": "Ghost", "phone": "9999999999"})
    ghost.create(opts.json())
    r = c.post("/api/webauthn/login/verify", json={"credential": ghost.get(K.login_options(c))})
    c.close()
    blocked = r.status_code == 400
    return result("blocked" if blocked else "allowed",
                  "A passkey the server never stored is unknown — login is refused.",
                  [step("Create a brand-new key pair and never finish registering it", who="attacker", kind="info"),
                   step("Sign in with that credential", who="attacker",
                        kind="blocked" if blocked else "warn", resp=r)])


def revoked_session(_legit=False):
    v = SCN.victim[0]
    c = K.logged_in_client(v)
    me1 = c.get("/api/me")
    steps = [step("Sign in and call /api/me", who="victim", kind="ok", resp=me1, note="Session works.")]
    if _legit:
        c.close()
        return result("allowed", "An active session can use the API.", steps)
    sessions = c.get("/api/sessions").json()
    current = next((s for s in sessions if s.get("current")), None)
    rv = c.delete(f"/api/sessions/{current['id']}")
    steps.append(step("Victim revokes that session (e.g. 'sign out a lost laptop')", who="victim", kind="info",
                      resp=rv, note="The session's cookie is now revoked."))
    me2 = c.get("/api/me")
    c.close()
    blocked = me2.status_code == 401
    steps.append(step("Call /api/me again with the SAME stolen cookie", who="attacker",
                      kind="blocked" if blocked else "warn", resp=me2,
                      note="Rejected — a revoked session is no longer accepted."))
    return result("blocked" if blocked else "allowed",
                  "A revoked session cookie is refused on the next request.", steps)


# ================================================================ assisted-access attacks

def _start_assist(owner_name, site=None):
    """Owner begins an assisted request. Returns (resp, req)."""
    c = K.client()
    body = {"username": owner_name}
    req = None
    if site is not None:
        verifier, challenge = K.pkce()
        loc = K.authorize(c, site, challenge, prompt="login").headers["location"]
        req = K.query(loc)["req"]
        body["req"] = req
    r = c.post("/api/assist", json=body)
    c.close()
    return r, req


def _not_started(r):
    """Outcome for an assisted request that never started — not an attack result either way."""
    return "rate limited" if r.status_code == 429 else "error"


def otp_guessing(_legit=False):
    owner = SCN.victim[1]
    if _legit:
        r, _ = _start_assist(owner)
        if r.status_code != 200:
            return result(_not_started(r), "Could not start (rate limit or no helper). Try again in a minute.",
                          [step("Start assisted sign-in", who="victim", kind="warn", resp=r)])
        data = r.json()
        otp = K.latest_otp(data["demo_phone"])
        with K.client() as c:
            v = c.post(f"/api/assist/{data['id']}/otp", json={"otp": otp},
                       headers={"X-Assist-Token": data["token"]})
        ok = v.status_code == 200
        return result("allowed" if ok else "blocked",
                      "The correct OTP from the owner's phone is accepted and a match number is shown.",
                      [step("Start assisted sign-in", who="victim", kind="ok", resp=r),
                       step("Enter the CORRECT OTP from the phone", who="victim", kind="ok" if ok else "warn", resp=v)])
    r, _ = _start_assist(owner)
    if r.status_code != 200:
        return result(_not_started(r), "Could not start (rate limit or no helper). Try again in a minute.",
                      [step("Start assisted sign-in", who="attacker", kind="warn", resp=r)])
    data = r.json()
    steps = [step("Start assisted sign-in for the victim (OTP goes to the victim's phone)", who="attacker",
                  kind="ok", resp=r)]
    hdr = {"X-Assist-Token": data["token"]}
    last = None
    with K.client() as c:
        for i in range(1, 7):
            last = c.post(f"/api/assist/{data['id']}/otp", json={"otp": f"{i:06d}"}, headers=hdr)
            steps.append(step(f"Guess OTP #{i}: {i:06d}", who="attacker", kind="info", resp=last))
            if last.status_code != 400 or "Too many" in str(last.text):
                break
    blocked = last is not None and ("Too many" in last.text or last.status_code == 400)
    if blocked:
        steps[-1]["kind"] = "blocked"
    return result("blocked" if blocked else "allowed",
                  "Wrong OTPs are limited. After 5 attempts the request is cancelled, so OTP guessing fails.", steps)


def citizen_refuses_assisted(_legit=False):
    owner = SCN.victim[1]
    r, _ = _start_assist(owner, site=K.CITIZEN)
    blocked = r.status_code == 400
    steps = [step("Try to start assisted sign-in for the Citizen Services Portal", who="attacker",
                  kind="blocked" if blocked else "warn", resp=r,
                  note="Refused — this website has assisted sign-in turned off (allow_assisted = false).")]
    # contrast: the college portal DOES allow it
    rc, _ = _start_assist(owner, site=K.COLLEGE)
    steps.append(step("For contrast: start the same for the College Portal", who="victim",
                      kind="ok" if rc.status_code == 200 else "info", resp=rc,
                      note="Allowed — the college portal permits assisted sign-in."))
    return result("blocked" if blocked else "allowed",
                  "Each website chooses its own policy. A bank/government service can require the user's own passkey.",
                  steps)


def assisted_flow_block_and_replay(_legit=False):
    """Run one real assisted login, then show (a) the assisted session can't manage the
    account, and (b) the approval can't be reused. _legit shows just the successful login."""
    owner_name = SCN.victim[1]
    helper_auth = SCN.helper[0]
    steps = []

    r, req = _start_assist(owner_name, site=K.COLLEGE)
    if r.status_code != 200:
        return result(_not_started(r), "Could not start (rate limit — assisted start is capped per minute). Try again shortly.",
                      [step("Start assisted sign-in", who="victim", kind="warn", resp=r)])
    steps.append(step("Owner (no passkey on this device) asks for help signing in to the College Portal",
                      who="victim", kind="ok", resp=r))
    data = r.json()
    oc = K.client()                      # owner's browser (no passkey)
    oc.cookies.clear()
    hdr = {"X-Assist-Token": data["token"]}
    otp = K.latest_otp(data["demo_phone"])
    otp_r = oc.post(f"/api/assist/{data['id']}/otp", json={"otp": otp}, headers=hdr)
    match = otp_r.json().get("match_code")
    steps.append(step("Owner proves phone with OTP; a match number is shown", who="victim", kind="ok", resp=otp_r,
                      note=f"Match number the owner reads out: {match}"))

    hc = K.logged_in_client(helper_auth)     # helper, signed in with their OWN passkey
    hc.get(f"/api/assist/{data['id']}/helper")
    aopts = hc.post(f"/api/assist/{data['id']}/approve/options").json()
    av = hc.post(f"/api/assist/{data['id']}/approve/verify",
                 json={"credential": helper_auth.get(aopts), "chosen": match})
    steps.append(step("Helper picks the matching number and approves with their OWN passkey", who="helper",
                      kind="ok" if av.status_code == 200 else "warn", resp=av))
    hc.close()

    done = oc.post(f"/api/assist/{data['id']}/complete", headers=hdr)
    steps.append(step("Owner completes — an assisted session is created", who="victim", kind="ok", resp=done,
                      note="The ID token carries acr = urn:kavach:acr:assisted, amr = [otp, helper]."))

    if _legit:
        oc.close()
        return result("allowed",
                      "A trusted helper approved one login with their own passkey. The owner never used a passkey, "
                      "and the helper never received the owner's account.", steps)

    # (a) assisted session tries to manage the account
    add = oc.post("/api/webauthn/add/options")
    steps.append(step("Attack A — use the assisted session to add a new passkey", who="attacker",
                      kind="blocked" if add.status_code == 403 else "warn", resp=add,
                      note="Rejected (403) — assisted sessions can view, but cannot change passkeys, helpers or recovery."))
    # (b) replay the approval
    again = oc.post(f"/api/assist/{data['id']}/complete", headers=hdr)
    oc.close()
    steps.append(step("Attack B — reuse the SAME approval again", who="attacker",
                      kind="blocked" if again.status_code == 400 else "warn", resp=again,
                      note="Rejected — the approval is single-use and already consumed."))
    blocked = add.status_code == 403 and again.status_code == 400
    return result("blocked" if blocked else "allowed",
                  "An assisted session is least-privilege (no account control) and each helper approval works exactly once.",
                  steps)


def stranger_approves(_legit=False):
    """A signed-in user who is NOT the victim's trusted helper tries to approve the victim's request."""
    owner_name = SCN.victim[1]
    r, _ = _start_assist(owner_name)
    if r.status_code != 200:
        return result(_not_started(r), "Could not start (rate limit — assisted start is capped per minute). Try again shortly.",
                      [step("Start assisted sign-in", who="victim", kind="warn", resp=r)])
    data = r.json()
    hdr = {"X-Assist-Token": data["token"]}
    steps = [step("Victim asks for help signing in", who="victim", kind="ok", resp=r)]
    with K.client() as oc:
        otp_r = oc.post(f"/api/assist/{data['id']}/otp", json={"otp": K.latest_otp(data["demo_phone"])}, headers=hdr)
    steps.append(step("Victim enters the phone OTP — request now waits for a helper", who="victim",
                      kind="ok", resp=otp_r))

    if _legit:
        hc = K.logged_in_client(SCN.helper[0])
        hv = hc.get(f"/api/assist/{data['id']}/helper")
        hc.close()
        ok = hv.status_code == 200
        steps.append(step("The REAL trusted helper opens the approval page", who="helper",
                          kind="ok" if ok else "warn", resp=hv,
                          note="Allowed — the helper sees three numbers to choose from."))
        _cancel_assist(data, steps)
        return result("allowed" if ok else "blocked",
                      "The helper the victim personally invited can open and approve the request.", steps)

    ac = K.logged_in_client(SCN.attacker[0])
    steps.append(step("Attacker signs in to Kavach with their OWN (valid) passkey", who="attacker", kind="ok",
                      note="The attacker is a real Kavach user — just not one the victim trusts."))
    view = ac.get(f"/api/assist/{data['id']}/helper")
    steps.append(step("Attacker opens the victim's approval page", who="attacker",
                      kind="blocked" if view.status_code == 403 else "warn", resp=view))
    opts = ac.post(f"/api/assist/{data['id']}/approve/options")
    steps.append(step("Attacker asks for an approval challenge anyway", who="attacker",
                      kind="blocked" if opts.status_code == 403 else "warn", resp=opts))
    ac.close()
    _cancel_assist(data, steps)
    blocked = view.status_code == 403 and opts.status_code == 403
    return result("blocked" if blocked else "allowed",
                  "Only a helper the owner invited AND who accepted can approve. Any other signed-in user gets 403 — "
                  "having a passkey is not enough, the trust relationship is checked on every helper request.", steps)


def _cancel_assist(data, steps):
    with K.client() as c:
        r = c.post(f"/api/assist/{data['id']}/cancel", headers={"X-Assist-Token": data["token"]})
    steps.append(step("Clean-up: victim cancels the pending request", who="victim", kind="info", resp=r))


# ================================================================ recovery attack

def wrong_recovery_code(_legit=False):
    victim_name = SCN.victim[1]
    code = SCN.victim[2] if _legit else "KVCH-AAAA-BBBB-CCCC"
    with K.client() as c:
        r = c.post("/api/recovery/start", json={"username": victim_name, "code": code})
    if _legit:
        ok = r.status_code == 200
        return result("allowed" if ok else "blocked",
                      "With the real recovery code, recovery reaches the SMS-code step. "
                      "(We stop here — completing it would remove the old passkeys.)",
                      [step("Start recovery with the CORRECT recovery code", who="victim", kind="ok" if ok else "warn", resp=r)])
    blocked = r.status_code == 400
    return result("blocked" if blocked else "allowed",
                  "A wrong recovery code is refused. Recovery needs the saved code AND an OTP to the registered phone.",
                  [step("Start recovery for the victim with a GUESSED recovery code", who="attacker",
                        kind="blocked" if blocked else "warn", resp=r)])


# ================================================================ network-edge attack

def spoofed_ip(_legit=False):
    """Fake a new X-Forwarded-For on every request to try to escape a per-IP rate limit.
    Uses the recovery-SMS-code limit (10/min), which a normal demo hardly touches."""
    import uuid

    steps = [step("Pick a rate-limited endpoint: recovery SMS-code check (10 tries/minute per IP)",
                  who="attacker", kind="info",
                  note="Each try uses a random request id, so it is counted and then answered 404 Not Found.")]
    limited_at = None
    with K.client() as c:
        for i in range(1, 13):
            fake = f"198.51.100.{i}"
            r = c.post(f"/api/recovery/{uuid.uuid4()}/otp", json={"otp": "123456"},
                       headers={"X-Forwarded-For": fake})
            hit = r.status_code == 429
            steps.append(step(f"Try #{i}, pretending to be {fake}", who="attacker",
                              kind="blocked" if hit else "info", resp=r,
                              note="Rate limit reached — the fake IP was ignored." if hit else ""))
            if hit:
                limited_at = i
                break
    blocked = limited_at is not None
    return result("blocked" if blocked else "allowed",
                  f"Still rate-limited after {limited_at} tries: Kavach ignores X-Forwarded-For unless it comes from one of "
                  "its own proxies (TRUSTED_PROXIES), so a client can't invent a new IP for each request."
                  if blocked else
                  "Not limited — the backend believed every fake IP. (Is it running the old client_ip() code?)",
                  steps)


# ================================================================ registry

REGISTRY = {
    "reuse_auth_code": {
        "group": "OpenID Connect",
        "title": "Reuse an authorization code",
        "attacker": "Steal a one-time sign-in code and exchange it twice.",
        "explain": "After you sign in, Kavach sends the website a short-lived 'code' that the website trades for your "
                   "tokens. If an attacker copies that code (from logs, browser history, a proxy) and trades it again, "
                   "they would get your tokens. Kavach marks each code as used the first time, so the second trade fails.",
        "threat": "Stolen authorization code",
        "test": "test_authorization_code_cannot_be_reused",
        "run": reuse_auth_code, "legit": lambda: reuse_auth_code(True),
    },
    "wrong_pkce": {
        "group": "OpenID Connect",
        "title": "Wrong PKCE verifier",
        "attacker": "Use a stolen code without the matching PKCE verifier.",
        "explain": "PKCE is a secret the website makes up before sign-in. It sends Kavach only a hash of it, and later "
                   "must show the original to redeem the code. An attacker who intercepts the code doesn't have that "
                   "secret, so even a fresh, unused stolen code is worthless to them.",
        "threat": "Intercepted code without proof-of-possession",
        "test": "test_wrong_pkce_verifier_is_rejected",
        "run": wrong_pkce, "legit": lambda: wrong_pkce(True),
    },
    "unregistered_redirect": {
        "group": "OpenID Connect",
        "title": "Unregistered redirect URI",
        "attacker": "Send the login result to an attacker's URL.",
        "explain": "The attacker crafts a sign-in link that says 'after login, send the result to attacker.example'. "
                   "Kavach only ever redirects to the exact addresses each website registered in advance, so it shows "
                   "an error page instead of handing your code to the attacker.",
        "threat": "Open redirect / token theft",
        "test": "test_unregistered_redirect_uri_is_not_followed",
        "run": unregistered_redirect, "legit": lambda: unregistered_redirect(True),
    },
    "wrong_client_secret": {
        "group": "OpenID Connect",
        "title": "Wrong client secret",
        "attacker": "Impersonate a website at the token endpoint.",
        "explain": "Each website has a secret shared only with Kavach. An attacker pretending to be the College Portal "
                   "at the token endpoint doesn't know it, so Kavach refuses them (invalid_client) before even looking "
                   "at the code.",
        "threat": "Client impersonation",
        "test": "test_wrong_client_secret_is_rejected",
        "run": wrong_client_secret, "legit": lambda: wrong_client_secret(True),
    },
    "forged_access_token": {
        "group": "OpenID Connect",
        "title": "Forge an access token",
        "attacker": "Edit your own token to say you are the victim, or strip its signature.",
        "explain": "An access token is a signed note from Kavach saying 'this is user X'. The attacker gets a real "
                   "token for themselves, rewrites the user id to the victim's, and tries the old 'alg: none' trick. "
                   "Kavach checks its RS256 signature on every use, so any edit makes the token invalid.",
        "threat": "Token tampering / forgery",
        "test": "(add: test_tampered_access_token_is_rejected)",
        "run": forged_access_token, "legit": lambda: forged_access_token(True),
    },
    "replay_login": {
        "group": "Passkeys",
        "title": "Replay a passkey login",
        "attacker": "Capture a signed login and send it again.",
        "explain": "Every passkey login signs a fresh random 'challenge' from Kavach. An attacker who records that "
                   "signed message and sends it again is replaying an answer to a question Kavach already crossed off, "
                   "so it is rejected.",
        "threat": "Replay attack",
        "test": "test_replayed_login_response_is_rejected",
        "run": replay_login, "legit": lambda: replay_login(True),
    },
    "lookalike_origin": {
        "group": "Passkeys",
        "title": "Look-alike site (origin binding)",
        "attacker": "Use a valid signature made for a phishing origin.",
        "explain": "A phishing site (kavach-login.xyz) tricks you into using your passkey. The signature is real, but "
                   "your device writes the site's address inside what it signs. Kavach sees the address isn't "
                   "localhost:3000 and refuses — this is why passkeys can't be phished like passwords.",
        "threat": "Phishing / wrong origin",
        "test": "test_signature_from_lookalike_site_is_rejected",
        "run": lookalike_origin, "legit": lambda: lookalike_origin(True),
    },
    "no_user_verification": {
        "group": "Passkeys",
        "title": "Login without fingerprint/PIN",
        "attacker": "Present a passkey assertion with no user verification.",
        "explain": "Someone picks up your unlocked laptop and tries to use the passkey without your fingerprint, face "
                   "or PIN. The device reports 'user not verified' inside the signed data, and Kavach requires that flag.",
        "threat": "Missing user verification",
        "test": "test_user_verification_is_required",
        "run": no_user_verification, "legit": lambda: no_user_verification(True),
    },
    "unknown_credential": {
        "group": "Passkeys",
        "title": "Unknown passkey",
        "attacker": "Sign in with a credential Kavach never stored.",
        "explain": "The attacker generates their own key pair and signs a login with it. Kavach only trusts public keys "
                   "it saved at registration, so a key it has never seen can't sign anyone in.",
        "threat": "Forged / unknown credential",
        "test": "test_unknown_passkey_is_rejected",
        "run": unknown_credential, "legit": lambda: unknown_credential(True),
    },
    "revoked_session": {
        "group": "Sessions",
        "title": "Revoked session cookie",
        "attacker": "Keep using a cookie after its session was revoked.",
        "explain": "You notice a session you don't recognise (or lose a laptop) and click 'sign out' on it. An attacker "
                   "who stole that session's cookie tries to keep using it. Kavach checks the session on every request, "
                   "so the revoked cookie stops working immediately.",
        "threat": "Stale / revoked session",
        "test": "(add: test_revoked_session_is_rejected)",
        "run": revoked_session, "legit": lambda: revoked_session(True),
    },
    "otp_guessing": {
        "group": "Assisted access",
        "title": "OTP guessing",
        "attacker": "Brute-force the owner's one-time code.",
        "explain": "Assisted sign-in starts with a 6-digit code sent to the owner's phone. The attacker doesn't have the "
                   "phone, so they guess. There are a million codes but only 5 tries, then the whole request is "
                   "cancelled.",
        "threat": "OTP brute force",
        "test": "(add: test_assist_otp_lockout)",
        "run": otp_guessing, "legit": lambda: otp_guessing(True),
    },
    "citizen_refuses_assisted": {
        "group": "Assisted access",
        "title": "Website refuses assisted login",
        "attacker": "Try assisted sign-in on a site that forbids it.",
        "explain": "Some websites (like the government Citizen Portal) decide that only your own passkey is good enough. "
                   "Kavach enforces each website's choice, so assisted sign-in can't be used to get into those sites.",
        "threat": "Policy bypass",
        "test": "test_site_that_refuses_assisted_sign_in",
        "run": citizen_refuses_assisted, "legit": None,
    },
    "assisted_flow_block_and_replay": {
        "group": "Assisted access",
        "title": "Assisted login: scope & replay",
        "attacker": "After a real assisted login, try to control the account and reuse the approval.",
        "explain": "A real assisted login runs end to end. Then the attacker tries to abuse it: (A) use the view-only "
                   "session to add their own passkey and take over the account, and (B) reuse the helper's approval "
                   "for a second login. Both are refused.",
        "threat": "Privilege escalation / approval replay",
        "test": "test_assisted_sign_in_end_to_end",
        "run": assisted_flow_block_and_replay, "legit": lambda: assisted_flow_block_and_replay(True),
    },
    "stranger_approves": {
        "group": "Assisted access",
        "title": "Stranger approves a login",
        "attacker": "A signed-in user who isn't the victim's helper tries to approve the victim's request.",
        "explain": "Assisted sign-in is only safe if the approver is someone the owner trusts. The attacker has a "
                   "genuine Kavach account and passkey, finds the victim's pending request, and tries to approve it. "
                   "Kavach checks the owner-helper relationship and answers 403.",
        "threat": "Unauthorised approver",
        "test": "test_non_helper_cannot_approve",
        "run": stranger_approves, "legit": lambda: stranger_approves(True),
    },
    "wrong_recovery_code": {
        "group": "Recovery",
        "title": "Wrong recovery code",
        "attacker": "Recover an account with a guessed code.",
        "explain": "If you lose every device, you recover with the code Kavach gave you at sign-up plus an SMS code. "
                   "The attacker guesses a recovery code to take over the account; it doesn't match, so recovery "
                   "never even reaches the SMS step.",
        "threat": "Account takeover via recovery",
        "test": "test_wrong_recovery_code",
        "run": wrong_recovery_code, "legit": lambda: wrong_recovery_code(True),
    },
    "spoofed_ip": {
        "group": "Network edge",
        "title": "Fake IP to dodge rate limits",
        "attacker": "Send a different fake X-Forwarded-For header on every request.",
        "explain": "Kavach limits how often one IP address can try things like SMS codes. The attacker writes a "
                   "made-up IP into the X-Forwarded-For header on each try, hoping Kavach counts each one as a new "
                   "visitor. Kavach only believes that header from its own proxies, so all tries are counted together "
                   "and the limit kicks in. (Uses the recovery-code limit for one minute.)",
        "threat": "Rate-limit bypass / IP spoofing",
        "test": "test_spoofed_forwarded_for_does_not_bypass_rate_limit",
        "run": spoofed_ip, "legit": None,
    },
}


def card_list():
    return [
        {"id": k, "group": v["group"], "title": v["title"], "attacker": v["attacker"],
         "explain": v["explain"], "threat": v["threat"], "test": v["test"],
         "has_legit": v["legit"] is not None}
        for k, v in REGISTRY.items()
    ]


def run(attack_id: str, legit: bool = False):
    SCN.setup()
    entry = REGISTRY[attack_id]
    fn = entry["legit"] if legit else entry["run"]
    if fn is None:
        return {"outcome": "n/a", "verdict": "No legitimate version for this card.", "steps": []}
    t0 = time.time()
    res = fn()
    res["ms"] = int((time.time() - t0) * 1000)
    res["legit"] = legit
    return res
