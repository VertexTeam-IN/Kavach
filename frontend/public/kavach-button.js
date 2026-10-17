/*!
 * Kavach drop-in "Continue with Kavach" button for plain HTML sites.
 *
 *   <div id="kavach-login"></div>
 *   <script src="http://localhost:3000/kavach-button.js"
 *           data-client-id="my-site"
 *           data-redirect-uri="https://my-site.example/auth/callback"></script>
 *
 * Clicking the button starts the standard OIDC Authorization Code + PKCE flow.
 * On your callback page, call:
 *
 *   const result = KavachLogin.handleCallback();   // { code, codeVerifier, redirectUri } or throws
 *
 * and send it to YOUR backend, which exchanges the code at {issuer}/token with its client secret.
 * The browser never sees tokens; the script only stores the PKCE verifier/state in sessionStorage.
 */
(function () {
  var script = document.currentScript;
  var issuer = (script && script.getAttribute("data-issuer")) || (script ? new URL(script.src).origin : location.origin);
  var clientId = script && script.getAttribute("data-client-id");
  var redirectUri = script && script.getAttribute("data-redirect-uri");
  var scope = (script && script.getAttribute("data-scope")) || "openid profile";
  var target = (script && script.getAttribute("data-target")) || "kavach-login";
  var KEY = "kavach_oidc";

  function b64url(bytes) {
    var s = "";
    bytes.forEach(function (b) { s += String.fromCharCode(b); });
    return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
  function random(n) {
    var a = new Uint8Array(n);
    crypto.getRandomValues(a);
    return b64url(a);
  }

  async function start() {
    var verifier = random(48);
    var digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
    var challenge = b64url(new Uint8Array(digest));
    var state = random(16);
    var nonce = random(16);
    sessionStorage.setItem(KEY, JSON.stringify({ verifier: verifier, state: state, nonce: nonce, redirectUri: redirectUri }));
    var url = new URL(issuer + "/authorize");
    url.search = new URLSearchParams({
      response_type: "code",
      client_id: clientId,
      redirect_uri: redirectUri,
      scope: scope,
      state: state,
      nonce: nonce,
      code_challenge: challenge,
      code_challenge_method: "S256",
    }).toString();
    location.href = url.toString();
  }

  function handleCallback() {
    var params = new URLSearchParams(location.search);
    var saved = JSON.parse(sessionStorage.getItem(KEY) || "null");
    sessionStorage.removeItem(KEY);
    if (params.get("error")) throw new Error(params.get("error_description") || params.get("error"));
    if (!saved || params.get("state") !== saved.state) throw new Error("State mismatch — possible CSRF, sign-in aborted");
    return { code: params.get("code"), codeVerifier: saved.verifier, nonce: saved.nonce, redirectUri: saved.redirectUri };
  }

  function render() {
    var el = document.getElementById(target);
    if (!el || !clientId || !redirectUri) return;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3Z" fill="#F2A93B"/></svg>' +
      "<span>Continue with Kavach</span>";
    btn.style.cssText =
      "display:inline-flex;align-items:center;gap:10px;padding:12px 20px;border:0;border-radius:12px;" +
      "background:#0F1B2D;color:#fff;font:600 15px system-ui,sans-serif;cursor:pointer";
    btn.addEventListener("click", start);
    el.appendChild(btn);
  }

  window.KavachLogin = { start: start, handleCallback: handleCallback };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render);
  else render();
})();
