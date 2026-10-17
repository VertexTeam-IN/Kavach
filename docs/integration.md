# Integrating a website with Kavach

Kavach is a standard **OpenID Connect provider**. Any platform that supports "custom / generic OpenID Connect
login" can add **Continue with Kavach** by configuration only.

## The contract

| Item | Value |
|---|---|
| Issuer | `http://localhost:3000` (your Kavach origin in production) |
| Discovery | `{issuer}/.well-known/openid-configuration` |
| Flow | Authorization Code + **PKCE (S256, required)** |
| Client auth | `client_secret_basic`, `client_secret_post`, or `none` for public clients |
| Scopes | `openid` (required), `profile` |
| ID token | RS256, keys at `{issuer}/.well-known/jwks.json` |
| Claims | `sub`, `name`, `preferred_username`, `acr`, `amr`, `auth_time`, `nonce`, `kavach_assisted_by` |
| Logout | `{issuer}/logout?client_id=…&post_logout_redirect_uri=…` |

## Four steps

1. **Register the website**
   ```bat
   cd backend && .venv\Scripts\activate
   python -m app.cli register-client --name "My Site" --redirect-uri https://my-site.example/callback
   ```
   Add `--no-assisted` to refuse assisted sign-ins, `--public` for SPAs/mobile apps without a secret.
2. **Paste issuer, client ID and secret** into the platform's OIDC settings.
3. **Add the button** — the platform's own login button, or the drop-in script:
   ```html
   <div id="kavach-login"></div>
   <script src="http://localhost:3000/kavach-button.js"
           data-client-id="my-site" data-redirect-uri="https://my-site.example/callback"></script>
   ```
4. **(Optional) Least privilege** — read `acr` from the ID token:
   - `urn:kavach:acr:passkey` → the user signed in with their own passkey
   - `urn:kavach:acr:assisted` → a trusted helper approved this one sign-in (`amr = ["otp","helper"]`,
     `kavach_assisted_by` = helper's name) → show view-only, block payments/changes.
   Or send `acr_values=urn:kavach:acr:passkey` to require a real passkey for that request.

## Platform examples

| Platform | Where |
|---|---|
| **Next.js (any)** | See `portals/college-portal/lib/oidc.js` — ~100 lines with `jose`, or Auth.js with a custom `oidc` provider |
| **Flask / FastAPI** | Authlib: `oauth.register(name="kavach", server_metadata_url=…, client_kwargs={"scope": "openid profile", "code_challenge_method": "S256"})` — see `portals/citizen-portal/app.py` |
| **Django** | `mozilla-django-oidc` or `django-allauth` OpenID Connect provider |
| **Express** | `openid-client` |
| **Spring Boot** | `spring.security.oauth2.client.provider.kavach.issuer-uri={issuer}` |
| **WordPress** | "OpenID Connect Generic Client" plugin |
| **Moodle** | Site admin → Server → OAuth 2 services → Custom |
| **Keycloak / Auth0** | Add Kavach as an external OIDC identity provider (brokering) |

Only Next.js and Flask are built and demonstrated; the others consume the same standard contract.
