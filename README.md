# 🌾 Dự án TTCS (Nhóm 3) — Truy xuất nguồn gốc & Giám sát chuỗi lạnh nông sản

Ứng dụng web toàn diện quản lý chuỗi cung ứng, truy xuất nguồn gốc lô hàng và giám sát nhiệt độ/độ ẩm chuỗi lạnh nông sản.

- **Backend:** Python 3.12+ / FastAPI / SQLAlchemy 2.0 / Alembic / PostgreSQL
- **Frontend:** React 19 / Vite / TypeScript
- **Container & DevOps:** Docker & Docker Compose / Nginx / GitHub Actions CI

---

## 📂 Cấu trúc thư mục dự án

```text
ttcs_n3/
├── .github/
│   └── workflows/
│       └── ci.yml               ← Pipeline CI tự động (Lint, Test, Docker Build)
├── .dockerignore                ← Loại trừ file rác khi build Docker
├── .gitignore                   ← Chặn commit node_modules, .venv, .env
├── CONTRIBUTING.md              ← Quy định làm việc nhóm (Branch, Commit, PR)
├── docker-compose.yml           ← Khởi động trọn gói Database + Backend + Frontend
├── Makefile                     ← Lệnh tắt tiện ích (make dev-backend, make test...)
├── README.md                    ← Tài liệu tổng quan dự án
│
├── backend/                     ← Dịch vụ Backend (FastAPI)
│   ├── alembic/                 ← Quản lý các phiên bản migration database
│   ├── alembic.ini              ← Cấu hình Alembic
│   ├── app/
│   │   ├── api/v1/endpoints/    ← Các route API (items, users, logs...)
│   │   ├── api/v1/router.py     ← Gom các router API v1
│   │   ├── core/                ← Config (Pydantic Settings), database engine
│   │   ├── models/              ← SQLAlchemy ORM models
│   │   ├── schemas/             ← Pydantic schemas (Request / Response validation)
│   │   ├── services/            ← Business logic nghiệp vụ
│   │   └── main.py              ← Điểm khởi chạy ứng dụng FastAPI
│   ├── tests/                   ← Unit & Integration tests (Pytest + HTTPX)
│   ├── Dockerfile               ← Multi-stage build image Backend
│   ├── pyproject.toml           ← Cấu hình Ruff (Lint/Format) và Pytest
│   ├── requirements.txt         ← Thư viện môi trường chạy thực tế (Production)
│   ├── requirements-dev.txt     ← Thư viện bổ sung khi code / test (Dev-only)
│   ├── .python-version          ← Phiên bản Python chuẩn
│   └── .env.example             ← Mẫu biến môi trường Backend
│
├── frontend/                    ← Dịch vụ Frontend (React + Vite + TypeScript)
│   ├── public/                  ← Tài nguyên tĩnh (favicon, icons)
│   ├── src/
│   │   ├── components/          ← UI components tái sử dụng
│   │   ├── hooks/               ← Custom React hooks (useApi...)
│   │   ├── pages/               ← Màn hình hoàn chỉnh
│   │   ├── services/            ← Gọi API Backend tập trung (api.ts)
│   │   ├── types/               ← TypeScript interfaces & types
│   │   ├── utils/               ← Hàm tiện ích chung
│   │   ├── App.tsx              ← Component gốc
│   │   └── main.tsx             ← Điểm khởi chạy React
│   ├── Dockerfile               ← Multi-stage build React + Nginx
│   ├── nginx.conf               ← Cấu hình Web Server Nginx (SPA fallback)
│   ├── package.json             ← Dependencies Node.js
│   ├── tsconfig*.json           ← Cấu hình TypeScript
│   ├── vite.config.ts           ← Cấu hình Vite bundler
│   ├── .nvmrc                   ← Phiên bản Node.js chuẩn
│   └── .env.example             ← Mẫu biến môi trường Frontend
│
└── docs/
    └── api.md                   ← Tài liệu mô tả các API endpoint cho nhóm
```

---

## 🚀 Hướng dẫn khởi chạy ứng dụng

### 👉 Cách 1: Khởi chạy bằng 1 lệnh Docker (Chuẩn task N3-1 / Demo)

*Yêu cầu:* Đã cài đặt và bật **Docker Desktop**.

Tại thư mục gốc dự án, chạy đúng 1 lệnh:
```bash
docker compose up --build -d
```

Sau khi hoàn tất:
- 🔌 **Backend Swagger API:** [http://localhost:8000/docs](http://localhost:8000/docs)
- 🌐 **Frontend Web:** [http://localhost:3000](http://localhost:3000)
- 🗄️ **Database PostgreSQL:** chạy nội bộ trong Docker network, không mở cổng host.

*Tắt hệ thống:*
```bash
docker compose down
```

---

### 👉 Cách 2: Khởi chạy trực tiếp từng dịch vụ (Local Development)

*Yêu cầu:* Cài đặt **Python 3.12+**, **Node.js 20+**, và **PostgreSQL 15+**.

#### 1. Chạy Backend (FastAPI):
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows (hoặc source .venv/bin/activate trên Linux/macOS)
pip install -r requirements-dev.txt

# Tạo file .env từ mẫu (sửa thông số kết nối DB nếu cần)
cp .env.example .env

# Chạy server với hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Chạy Frontend (React):
Mở một cửa sổ Terminal mới:
```bash
cd frontend
npm install
npm run dev
```
Frontend dùng cổng `3000`; API mặc định tại `http://localhost:8000`.

---

## 🛠️ Lệnh tắt tiện ích (Makefile)

Nếu máy bạn có cài đặt `make`:
- `make dev-backend`: Chạy nhanh Backend
- `make dev-frontend`: Chạy nhanh Frontend
- `make test`: Chạy toàn bộ test Pytest
- `make lint`: Kiểm tra code style (Ruff + Oxlint)
- `make lint-fix`: Tự động sửa lỗi code style
- `make migrate`: Cập nhật schema database lên phiên bản mới nhất

---

## 🤝 Quy định làm việc & Đóng góp mã nguồn

Toàn bộ 10 thành viên nhóm tuân thủ nghiêm ngặt quy trình chia nhánh, format commit và tạo Pull Request tại file:  
👉 **[CONTRIBUTING.md](./CONTRIBUTING.md)**
