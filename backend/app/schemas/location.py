from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=500)

    @field_validator("name", "address")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tên và địa chỉ không được để trống.")
        return value.strip()


class LocationRead(LocationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID


class LotMove(BaseModel):
    location_id: UUID
    note: str | None = Field(default=None, max_length=500)


class LotConsume(BaseModel):
    note: str | None = Field(default=None, max_length=500)
