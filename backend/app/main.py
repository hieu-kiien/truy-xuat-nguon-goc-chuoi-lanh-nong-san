from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import auth
from app.api.v1.router import api_router, demo_router
from app.core.config import settings

app = FastAPI(
    title="TTCS API",
    description="Backend API cho dự án nhóm TTCS",
    version="1.0.0",
)

# Cấu hình CORS — cho phép Frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn tất cả routes từ api/v1
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(demo_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "message": "TTCS Backend đang chạy ✅"}
