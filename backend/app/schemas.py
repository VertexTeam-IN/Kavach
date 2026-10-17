"""Pydantic request bodies (validated automatically by FastAPI)."""
import re

from pydantic import BaseModel, Field, field_validator

USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,32}$")


class RegisterStart(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    display_name: str = Field(min_length=1, max_length=128)
    phone: str = Field(min_length=4, max_length=30)

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip().lower().lstrip("@")
        if not USERNAME_RE.match(v):
            raise ValueError("Use 3-32 characters: lowercase letters, numbers, . _ -")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = re.sub(r"[\s\-\(\)\.]", "", v.strip())
        if not re.fullmatch(r"\+?\d{6,16}", v):
            raise ValueError("Enter a valid mobile number (6 to 16 digits)")
        return v


class CredentialBody(BaseModel):
    credential: dict
    req: str | None = None        # pending OIDC sign-in request id (from /authorize)
    label: str | None = Field(default=None, max_length=64)


class ConsentBody(BaseModel):
    req: str
    allow: bool


class ContinueBody(BaseModel):
    req: str


class HelperInvite(BaseModel):
    username: str = Field(min_length=3, max_length=32)


class AssistStart(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    req: str | None = None


class OtpBody(BaseModel):
    otp: str = Field(min_length=4, max_length=8)


class ApproveVerify(BaseModel):
    credential: dict
    chosen: str = Field(min_length=1, max_length=3)


class RecoveryStart(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    code: str = Field(min_length=8, max_length=40)
    req: str | None = None


class PasskeyRename(BaseModel):
    label: str = Field(min_length=1, max_length=64)
