from fastapi import APIRouter, Depends

from app.api.v1.endpoints import items
from app.core.authorization import enforce_route_permission

api_router = APIRouter(dependencies=[Depends(enforce_route_permission)])
api_router.include_router(items.router, prefix="/items", tags=["items"])
