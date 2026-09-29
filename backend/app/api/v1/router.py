from fastapi import APIRouter

from app.api.v1.endpoints import items

api_router = APIRouter()

# Thêm các endpoint groups vào đây
api_router.include_router(items.router, prefix="/items", tags=["items"])
