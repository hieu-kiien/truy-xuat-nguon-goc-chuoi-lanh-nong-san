"""Schemas for the public route map of a lot (N3-70)."""

from pydantic import BaseModel, Field


class RoutePointRead(BaseModel):
    """One point of the public route, rounded to the district level."""

    order: int
    name: str
    kind: str
    latitude: float
    longitude: float


class PublicRouteRead(BaseModel):
    """The public route of a lot: the origin and the main stops in order."""

    points: list[RoutePointRead] = Field(default_factory=list)
    precision_note: str = "Các điểm được làm tròn về cấp xã hoặc huyện, không hiện toạ độ chính xác của thửa."
