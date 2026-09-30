from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    farm_id: UUID
    name: str
