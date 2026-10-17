"""Citizen Services Portal — OIDC client #2 of Kavach, built with an off-the-shelf library (Authlib).

No Kavach-specific code: just the issuer URL, client ID and secret. Authlib reads discovery,
does PKCE, exchanges the code and verifies the RS256 ID token (iss, aud, exp, nonce, signature).

Run:  flask --app app run -h 127.0.0.1 -p 5000
"""
import os

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for

load_dotenv()
# Allow http://localhost during the demo (Authlib requires HTTPS otherwise)
os.environ.setdefault("AUTHLIB_INSECURE_TRANSPORT", "1")

ISSUER = os.getenv("KAVACH_ISSUER", "http://localhost:3000")
APP_URL = os.getenv("APP_URL", "http://127.0.0.1:5000")
CLIENT_ID = os.getenv("KAVACH_CLIENT_ID", "citizen-portal")
REDIRECT_URI = os.getenv("REDIRECT_URI", f"{APP_URL}/callback")

app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET", "citizen-portal-session-secret-change-me")
app.config.update(SESSION_COOKIE_NAME="citizen_sid", SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

oauth = OAuth(app)
oauth.register(
    name="kavach",
    client_id=CLIENT_ID,
    client_secret=os.getenv("KAVACH_CLIENT_SECRET", ""),
    server_metadata_url=f"{ISSUER}/.well-known/openid-configuration",
    client_kwargs={"scope": "openid profile", "code_challenge_method": "S256"},
)


@app.route("/")
def index():
    return render_template("index.html", user=session.get("user"), error=request.args.get("error"))


@app.route("/login")
def login():
    return oauth.kavach.authorize_redirect(REDIRECT_URI)


@app.route("/callback")
def callback():
    if request.args.get("error"):
        return redirect(url_for("index", error=request.args.get("error_description") or request.args["error"]))
    try:
        token = oauth.kavach.authorize_access_token()
    except Exception as exc:  # state mismatch, invalid code, bad signature...
        return redirect(url_for("index", error=f"Sign-in failed: {exc}"))
    claims = token["userinfo"]  # verified ID token claims
    session["user"] = {
        "sub": claims["sub"],
        "name": claims.get("name"),
        "username": claims.get("preferred_username"),
        "acr": claims.get("acr"),
    }
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return redirect(url_for("index"))
    return render_template("dashboard.html", user=user)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(f"{ISSUER}/logout?client_id={CLIENT_ID}&post_logout_redirect_uri={APP_URL}/")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
