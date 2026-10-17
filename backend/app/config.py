"""Application settings, read from environment variables / backend/.env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://kavach:kavach@127.0.0.1:5432/kavach"

    # WebAuthn relying party
    RP_ID: str = "localhost"
    RP_NAME: str = "Kavach"
    ORIGIN: str = "http://localhost:3000"

    # OIDC
    ISSUER: str = "http://localhost:3000"

    # Cookies / sessions
    COOKIE_NAME: str = "kavach_sid"
    COOKIE_SECURE: bool = False
    SESSION_TTL_MIN: int = 480          # normal passkey session: 8 hours
    ASSISTED_SESSION_TTL_MIN: int = 15  # assisted session: 15 minutes

    # Lifetimes (seconds)
    CHALLENGE_TTL_SEC: int = 120
    AUTH_REQUEST_TTL_SEC: int = 600
    AUTH_CODE_TTL_SEC: int = 60
    ID_TOKEN_TTL_SEC: int = 300
    ACCESS_TOKEN_TTL_SEC: int = 300
    ASSIST_OTP_TTL_SEC: int = 300
    ASSIST_APPROVAL_TTL_SEC: int = 180
    RECOVERY_TTL_SEC: int = 600

    # Files
    KEY_PATH: str = "keys/kavach_private.pem"
    SEED_CLIENTS_PATH: str = "seed_clients.json"

    DEMO_MODE: bool = True

    # Comma-separated IPs of YOUR reverse proxies (e.g. nginx/Caddy in front of the app).
    # X-Forwarded-For is only believed when the request arrives from one of these; otherwise any
    # client could put a fake IP there and dodge the per-IP rate limits. Empty = trust no one,
    # which is right for the local setup (the Next.js proxy does not add X-Forwarded-For).
    TRUSTED_PROXIES: str = ""


settings = Settings()
