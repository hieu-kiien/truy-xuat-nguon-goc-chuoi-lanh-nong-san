"""Schemas for the in-app notification centre (N3-56)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationRead(BaseModel):
    """One notification shown in the notification centre."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    title: str
    body: str
    link_path: str
    lot_id: UUID | None = None
    lot_code: str | None = None
    created_at: datetime
    read_at: datetime | None = None

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


class NotificationListRead(BaseModel):
    """The notification centre payload: the list plus the unread badge count."""

    items: list[NotificationRead] = Field(default_factory=list)
    unread_count: int = Field(default=0, ge=0)
    generated_at: datetime
