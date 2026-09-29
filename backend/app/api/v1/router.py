from fastapi import APIRouter, Depends

from app.api.v1.endpoints import items
from app.core.authorization import enforce_route_permission

api_router = APIRouter(dependencies=[Depends(enforce_route_permission)])
demo_router = APIRouter()

# Đăng ký API nghiệp vụ tại api_router để mặc định yêu cầu quyền.
# Endpoint mẫu cũ được giữ công khai, tách khỏi API nghiệp vụ để tương thích.
demo_router.include_router(items.router, prefix="/items", tags=["items"])
