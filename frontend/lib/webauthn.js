// Passkey ceremonies. @simplewebauthn/browser calls navigator.credentials.create()/get()
// (which opens Windows Hello / phone QR) and handles the base64url encoding.
import { startAuthentication, startRegistration } from "@simplewebauthn/browser";

import { api } from "./api";

export async function registerPasskey(data, req) {
  const optionsJSON = await api("/api/webauthn/register/options", {
    method: "POST",
    body: data,
  });
  const credential = await startRegistration({ optionsJSON });
  return api("/api/webauthn/register/verify", { method: "POST", body: { credential, req } });
}

export async function loginWithPasskey(req) {
  const optionsJSON = await api("/api/webauthn/login/options", {
    method: "POST",
  });
  const credential = await startAuthentication({ optionsJSON });
  return api("/api/webauthn/login/verify", { method: "POST", body: { credential, req } });
}

export async function addBackupPasskey(label) {
  const optionsJSON = await api("/api/webauthn/add/options", {
    method: "POST",
  });
  const credential = await startRegistration({ optionsJSON });
  return api("/api/webauthn/add/verify", { method: "POST", body: { credential, label } });
}

/** Helper approves an assisted request with THEIR OWN passkey + the number the owner read out. */
export async function helperApprove(assistId, chosen) {
  const optionsJSON = await api(`/api/assist/${assistId}/approve/options`, { method: "POST" });
  const credential = await startAuthentication({ optionsJSON });
  return api(`/api/assist/${assistId}/approve/verify`, {
    method: "POST",
    body: { credential, chosen },
  });
}

/** Recovery: register a brand-new passkey on this device after code + OTP were verified. */
export async function recoveryRegister(recoveryId, token) {
  const headers = { "X-Recovery-Token": token };
  const optionsJSON = await api(`/api/recovery/${recoveryId}/register/options`, {
    method: "POST",
    headers,
  });
  const credential = await startRegistration({ optionsJSON });
  return api(`/api/recovery/${recoveryId}/register/verify`, {
    method: "POST",
    headers,
    body: { credential, label: "New device (recovered)" },
  });
}
