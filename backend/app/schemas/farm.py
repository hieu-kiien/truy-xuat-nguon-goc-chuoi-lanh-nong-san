from decimal import Decimal, InvalidOperation
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FarmFields(BaseModel):
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


class FarmRead(FarmFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
