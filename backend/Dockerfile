# ==============================================================================
# Dockerfile cho Backend (FastAPI + Python)
# Sử dụng Multi-stage build để tối ưu dung lượng Image
# ==============================================================================

# Stage 1: Builder (Cài đặt thư viện)
FROM python:3.12-slim AS builder

WORKDIR /app

# Cài đặt các công cụ cần thiết cho build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Tối ưu Docker Cache: Chỉ copy requirements trước
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Final Runtime (Image chạy thực tế siêu nhẹ)
FROM python:3.12-slim AS final

WORKDIR /app

# Cài đặt thư viện runtime cho PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy các gói Python đã cài từ builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy toàn bộ mã nguồn backend
COPY . .

# Mở cổng API
EXPOSE 8000

# Lệnh khởi động server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
