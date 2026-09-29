from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class SessionUser(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    organization_id: UUID
    organization_name: str
    organization_type: str
    role: str
