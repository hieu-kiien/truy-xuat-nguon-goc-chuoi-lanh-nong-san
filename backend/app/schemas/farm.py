from decimal import Decimal, InvalidOperation
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FarmFields(BaseModel):
    # Reject unknown keys so a client cannot smuggle `id` or `organization_id`
    # into a create/update body and hijack another tenant's row.
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    area_ha: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    latitude: Decimal = Field(ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal = Field(ge=-180, le=180, max_digits=9, decimal_places=6)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Tên thửa đất không được để trống.")
        return value.strip()

    @field_validator("area_ha", mode="before")
    @classmethod
    def validate_positive_area(cls, value: object) -> Decimal:
        if isinstance(value, bool):
            raise ValueError("Diện tích phải là một số lớn hơn 0 ha.")
        try:
            area = Decimal(str(value))
        except InvalidOperation as error:
            raise ValueError("Diện tích phải là một số hợp lệ.") from error
        if not area.is_finite() or area <= 0:
            raise ValueError("Diện tích phải lớn hơn 0 ha.")
        return area


class FarmCreate(FarmFields):
    pass


class FarmUpdate(FarmFields):
    pass


class FarmPatch(BaseModel):
    """Partial update. Renaming a farm must not touch its identifier.

    Because the primary key is never part of the payload, a rename cannot
    detach lots that reference the farm: `farms.id` is the stable relation key.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    area_ha: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)
    latitude: Decimal | None = Field(
        default=None, ge=-90, le=90, max_digits=9, decimal_places=6
    )
    longitude: Decimal | None = Field(
        default=None, ge=-180, le=180, max_digits=9, decimal_places=6
    )

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Tên thửa đất không được để trống.")
        return value.strip()

    @field_validator("area_ha", mode="before")
    @classmethod
    def validate_positive_area(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("Diện tích phải là một số lớn hơn 0 ha.")
        try:
            area = Decimal(str(value))
        except InvalidOperation as error:
            raise ValueError("Diện tích phải là một số hợp lệ.") from error
        if not area.is_finite() or area <= 0:
            raise ValueError("Diện tích phải lớn hơn 0 ha.")
        return area


class FarmRead(FarmFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
