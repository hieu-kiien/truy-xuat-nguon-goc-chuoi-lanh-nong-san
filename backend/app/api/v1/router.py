from fastapi import APIRouter

from app.api.v1.endpoints import auth, items

api_router = APIRouter()

# Thêm các endpoint groups vào đây
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
