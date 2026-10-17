"""Friendly names for passkey authenticators.

At registration the authenticator reports an AAGUID — a model identifier ("which kind of passkey
is this?"), not a per-device id. A subset of the community list at
github.com/passkeydeveloper/passkey-authenticator-aaguids is enough to name the common ones.
Many authenticators send all zeros (no attestation); then we fall back to the transports.
"""

ZERO_AAGUID = "00000000-0000-0000-0000-000000000000"

KNOWN = {
    "08987058-cadc-4b81-b6e1-30de50dcbe96": "Windows Hello",
    "9ddd1817-af5a-4672-a2b9-3e3dd95000a9": "Windows Hello",
    "6028b017-b1d4-4c02-b4b3-afcdafc96bb2": "Windows Hello",
    "ea9b8d66-4d01-1d21-3ce4-b6b48cb575d4": "Google Password Manager",
    "adce0002-35bc-c60a-648b-0b25f1f05503": "Chrome on Mac",
    "fbfc3007-154e-4ecc-8c0b-6e020557d7bd": "iCloud Keychain",
    "dd4ec289-e01d-41c9-bb89-70fa845d4bf2": "iCloud Keychain (managed)",
    "53414d53-554e-4700-0000-000000000000": "Samsung Pass",
    "bada5566-a7aa-401f-bd96-45619a55120d": "1Password",
    "d548826e-79b4-db40-a3d8-11116f7e8349": "Bitwarden",
    "531126d6-e717-415c-9320-3d9aa6981239": "Dashlane",
    "cb69481e-8ff7-4039-93ec-0a2729a154a8": "YubiKey 5",
    "ee882879-721c-4913-9775-3dfcce97072a": "YubiKey 5 NFC",
    "fa2b99dc-9e39-4257-8f92-4a30d23c4118": "YubiKey 5 NFC",
    "2fc0579f-8113-47ea-b116-bb5a8db9202a": "YubiKey 5 NFC",
}


def model_name(aaguid: str | None, transports: list | None) -> str | None:
    """'Windows Hello', 'YubiKey 5 NFC', … or a generic kind, or None if nothing is known."""
    if aaguid and aaguid != ZERO_AAGUID and aaguid in KNOWN:
        return KNOWN[aaguid]
    t = set(transports or [])
    if "hybrid" in t:
        return "Phone (via QR code)"
    if t & {"usb", "nfc", "ble"} and "internal" not in t:
        return "Security key"
    if "internal" in t:
        return "Built into this device"
    return None
