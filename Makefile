# ==============================================================================
# Makefile — Lệnh tắt cho toàn bộ dự án TTCS
# Dùng: make <lệnh>   Ví dụ: make dev-backend
# ==============================================================================

.PHONY: help install dev-backend dev-frontend test lint migrate

# Hiển thị danh sách lệnh khi gõ `make` không có tham số
help:
	@echo ""
	@echo "  TTCS — Các lệnh có sẵn:"
	@echo ""
	@echo "  make install        Cài tất cả thư viện (backend + frontend)"
	@echo "  make dev-backend    Chạy Backend (FastAPI + hot-reload)"
	@echo "  make dev-frontend   Chạy Frontend (Vite dev server)"
	@echo "  make test           Chạy toàn bộ test backend"
	@echo "  make lint           Kiểm tra code style (ruff + prettier)"
	@echo "  make lint-fix       Tự sửa lỗi code style"
	@echo "  make migrate        Áp dụng migration DB mới nhất"
	@echo "  make migration msg  Tạo migration mới: make migration msg='ten migration'"
	@echo ""

# ─── Cài đặt ──────────────────────────────────────────────────────────────────
install:
	cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
	cd frontend && npm install

# ─── Chạy Dev ─────────────────────────────────────────────────────────────────
dev-backend:
	cd backend && .venv/Scripts/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# ─── Test ─────────────────────────────────────────────────────────────────────
test:
	cd backend && .venv/Scripts/pytest tests/ -v

# ─── Lint & Format ────────────────────────────────────────────────────────────
lint:
	cd backend && .venv/Scripts/ruff check app/ tests/
	cd frontend && npm run lint

lint-fix:
	cd backend && .venv/Scripts/ruff check --fix app/ tests/ && .venv/Scripts/ruff format app/ tests/

# ─── Database Migration ───────────────────────────────────────────────────────
migrate:
	cd backend && .venv/Scripts/alembic upgrade head

migration:
	cd backend && .venv/Scripts/alembic revision --autogenerate -m "$(msg)"
