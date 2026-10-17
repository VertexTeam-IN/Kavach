import { ApiError } from "./api";

/** Turn WebAuthn / API errors into messages a non-technical user understands. */
export function friendly(err) {
  if (err instanceof ApiError) return err.message;
  const name = err?.name;
  const message = err?.message ?? "";
  switch (name) {
    case "NotAllowedError":
      return "Sign-in was cancelled or timed out. Please try again.";
    case "InvalidStateError":
      return "This device already has a passkey for this account. Sign in instead.";
    case "SecurityError":
      return "Passkeys only work at http://localhost:3000 — check the address bar.";
    case "NotSupportedError":
      return "This browser or device does not support passkeys. Try Chrome or Edge with Windows Hello set up.";
    case "AbortError":
      return "The request was interrupted. Please try again.";
  }
  if (message.includes("Failed to fetch"))
    return "Can't reach the Kavach server. Is the backend running?";
  return message || "Something went wrong. Please try again.";
}
