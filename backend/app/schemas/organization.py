"""Schemas for the caller's own organization (N3-57, N3-30)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class OrganizationRead(BaseModel):
    """The organization of the signed-in user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    organization_type: str
    contact_email: str | None = None


class ContactEmailUpdate(BaseModel):
    """New official contact address of the organization."""

    contact_email: str | None = None

    @field_validator("contact_email")
    @classmethod
    def normalize_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip().lower()
        if not trimmed:
            return None
        if "@" not in trimmed or trimmed.startswith("@") or trimmed.endswith("@"):
            raise ValueError("Địa chỉ email không hợp lệ.")
        return trimmed


class InvitationCreate(BaseModel):
    """Request to invite a new member into the organization."""

    email: EmailStr
    role_code: str = Field(min_length=1, max_length=48)


class InvitationRead(BaseModel):
    """One invitation of the organization."""

    id: UUID
    organization_id: UUID
    organization_name: str
    email: str
    role_code: str
    status: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None


class InvitationCreated(InvitationRead):
    """A freshly created invitation, with its single-use link.

    The link is returned only once, right after the invitation is made, so the
    administrator can pass it on when the e-mail channel is not configured yet.
    It is never returned by the listing endpoint.
    """

    invitation_url: str


class InvitationPreview(BaseModel):
    """Public details of an invitation, shown to the invited person."""

    email: str
    organization_id: str
    organization_name: str
    role_code: str
    expires_at: str


class InvitationAccept(BaseModel):
    """The invited person sets a password and joins."""

    password: str = Field(min_length=12, max_length=1024)
    full_name: str = Field(min_length=1, max_length=200)


class InvitationAccepted(BaseModel):
    """Result of accepting an invitation."""

    user_id: str
    organization_id: str
    role_code: str
    email: str


class MemberRead(BaseModel):
    """One member of the organization."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role_code: str
    is_active: bool
    locked_until: datetime | None = None
