"""A software passkey authenticator for tests.

It does exactly what Windows Hello does cryptographically — creates a P-256 key pair per
credential, returns the public key at registration, and signs (authenticatorData ||
SHA256(clientDataJSON)) at login — so the whole flow can be tested without a fingerprint.
"""
import base64
import hashlib
import json
import os

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

FLAG_UP, FLAG_UV, FLAG_AT = 0x01, 0x04, 0x40


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class SoftAuthenticator:
    def __init__(self, rp_id: str = "localhost", origin: str = "http://localhost:3000"):
        self.rp_id = rp_id
        self.origin = origin
        self.creds: dict[bytes, dict] = {}

    @property
    def rp_hash(self) -> bytes:
        return hashlib.sha256(self.rp_id.encode()).digest()

    # navigator.credentials.create()
    def create(self, options: dict, *, origin: str | None = None, user_verified: bool = True) -> dict:
        key = ec.generate_private_key(ec.SECP256R1())
        nums = key.public_key().public_numbers()
        cose = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: nums.x.to_bytes(32, "big"), -3: nums.y.to_bytes(32, "big")})
        cred_id = os.urandom(16)
        flags = FLAG_UP | FLAG_AT | (FLAG_UV if user_verified else 0)
        auth_data = (self.rp_hash + bytes([flags]) + (0).to_bytes(4, "big") + b"\x00" * 16
                     + len(cred_id).to_bytes(2, "big") + cred_id + cose)
        client_data = json.dumps({
            "type": "webauthn.create", "challenge": options["challenge"],
            "origin": origin or self.origin, "crossOrigin": False,
        }).encode()
        self.creds[cred_id] = {"key": key, "user_handle": unb64(options["user"]["id"]), "count": 0}
        return {
            "id": b64(cred_id), "rawId": b64(cred_id), "type": "public-key",
            "response": {
                "clientDataJSON": b64(client_data),
                "attestationObject": b64(cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})),
                "transports": ["internal"],
            },
            "clientExtensionResults": {}, "authenticatorAttachment": "platform",
        }

    # navigator.credentials.get()
    def get(self, options: dict, *, origin: str | None = None, user_verified: bool = True,
            cred_id: bytes | None = None) -> dict:
        if cred_id is None:
            allowed = [unb64(c["id"]) for c in options.get("allowCredentials") or []]
            candidates = [c for c in self.creds if not allowed or c in allowed]
            if not candidates:
                raise RuntimeError("No matching passkey on this soft authenticator")
            cred_id = candidates[0]
        cred = self.creds[cred_id]
        cred["count"] += 1
        flags = FLAG_UP | (FLAG_UV if user_verified else 0)
        auth_data = self.rp_hash + bytes([flags]) + cred["count"].to_bytes(4, "big")
        client_data = json.dumps({
            "type": "webauthn.get", "challenge": options["challenge"],
            "origin": origin or self.origin, "crossOrigin": False,
        }).encode()
        signature = cred["key"].sign(auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256()))
        return {
            "id": b64(cred_id), "rawId": b64(cred_id), "type": "public-key",
            "response": {
                "clientDataJSON": b64(client_data),
                "authenticatorData": b64(auth_data),
                "signature": b64(signature),
                "userHandle": b64(cred["user_handle"]),
            },
            "clientExtensionResults": {}, "authenticatorAttachment": "platform",
        }
