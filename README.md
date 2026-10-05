# Hệ thống Truy xuất Nguồn gốc và Giám sát Chuỗi lạnh Nông sản

**Tình hình Sprint 2 (2026-10-05):** [docs/SPRINT-2-PLAN.md](docs/SPRINT-2-PLAN.md) — snapshot Jira, Git và các vướng mắc tích hợp; có thể tái tạo khi nguồn đổi.
**Bàn giao máy local (2026-10-03):** [HANDOFF.md](HANDOFF.md) — trạng thái merge/kiểm thử, cách chạy local và vướng mắc triển khai domain.

Ứng dụng quản lý quy trình canh tác, theo dõi lô hàng và giám sát điều kiện bảo quản nông sản theo thời gian thực.

## Công nghệ sử dụng

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL
- **Frontend:** React 19, TypeScript, Vite
- **Hạ tầng & CI/CD:** Docker, Docker Compose, Nginx, GitHub Actions, Render

## Cấu trúc dự án

```text
.
├── .github/workflows/       # Cấu hình CI/CD tự động (lint, test, build, deploy)
├── backend/
│   ├── alembic/             # Quản lý phiên bản migration cơ sở dữ liệu
│   ├── app/
│   │   ├── api/v1/          # Định tuyến RESTful API (endpoints, router)
│   │   ├── core/            # Cấu hình ứng dụng và kết nối cơ sở dữ liệu
│   │   ├── models/          # Khai báo SQLAlchemy ORM models
│   │   ├── schemas/         # Khai báo Pydantic schemas (validation & serialization)
│   │   ├── services/        # Xử lý nghiệp vụ (business logic)
│   │   └── main.py          # Điểm khởi chạy ứng dụng FastAPI
│   ├── tests/               # Kiểm thử đơn vị và tích hợp (Pytest)
│   ├── Dockerfile           # Đóng gói container Backend
│   ├── pyproject.toml       # Cấu hình Ruff linter, formatter và Pytest
│   ├── requirements.txt     # Thư viện môi trường production
│   └── requirements-dev.txt # Thư viện môi trường phát triển
├── frontend/
│   ├── public/              # Tài nguyên tĩnh
│   ├── src/
│   │   ├── components/      # Các thành phần giao diện tái sử dụng
│   │   ├── hooks/           # Custom React hooks
│   │   ├── pages/           # Các trang giao diện chính
│   │   ├── services/        # Tầng giao tiếp API với Backend
│   │   ├── types/           # Định nghĩa kiểu dữ liệu TypeScript
│   │   └── utils/           # Các hàm tiện ích dùng chung
│   ├── Dockerfile           # Đóng gói container Frontend (Node build + Nginx)
│   ├── nginx.conf           # Cấu hình định tuyến SPA cho Nginx
│   └── package.json         # Quản lý thư viện và script Frontend
├── docs/                    # Tài liệu đặc tả kỹ thuật và API
├── docker-compose.yml       # Khởi chạy toàn bộ hệ thống bằng Docker
├── Makefile                 # Tập hợp các lệnh tắt phục vụ phát triển
├── render.yaml              # Khai báo hạ tầng đám mây (Infrastructure as Code)
└── CONTRIBUTING.md          # Quy chuẩn làm việc nhóm và đóng góp mã nguồn
```

## Hướng dẫn cài đặt và khởi chạy

### 1. Khởi chạy nhanh bằng Docker Compose

Yêu cầu máy tính đã cài đặt và bật **Docker Desktop**. Chạy lệnh sau tại thư mục gốc của dự án:

```bash
docker compose up --build -d
```

Docker Compose bật chế độ demo cho môi trường phát triển, vì vậy có thể dùng các nút **Vào demo/Đổi nhanh phiên** mà không cần một mật khẩu demo được công khai trong mã nguồn. Chế độ này bị chặn khi `APP_ENV=production`.

Sau khi các container khởi động hoàn tất:
- **Giao diện Web:** http://localhost:5173
- **Tài liệu API (Swagger UI):** http://localhost:8000/docs
- **Cơ sở dữ liệu PostgreSQL:** `localhost:5432` (Database: `ttcs_db`, User quản trị: `admin`)
- **Kết nối ứng dụng:** backend dùng role `ttcs_app` tách biệt để chính sách PostgreSQL RLS được áp dụng trên request runtime.

Để dừng toàn bộ dịch vụ:
```bash
docker compose down
```

### 2. Khởi chạy trực tiếp trên máy (Môi trường phát triển)

#### Backend (FastAPI)

```bash
cd backend
python -m venv .venv

# Kích hoạt môi trường ảo (Windows)
.venv\Scripts\activate
# Hoặc trên Linux/macOS: source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env

# Sau khi đã điền DB_PASSWORD và DB_ADMIN_PASSWORD trong .env:
python -m app.bootstrap_db_role
alembic upgrade head
python -m app.seed_demo

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`bootstrap_db_role` tạo/cập nhật role runtime `ttcs_app` theo nguyên tắc least privilege. Migration và seed dùng tài khoản quản trị riêng; API request dùng `ttcs_app`. Không cấu hình hai vai trò này thành cùng một database user.

#### Frontend (React + Vite)

Mở một cửa sổ terminal mới:

```bash
cd frontend
npm ci
cp .env.example .env.local

npm run dev
```

Để bật đăng nhập demo một chạm khi chạy trực tiếp, đặt `ENABLE_DEMO_LOGIN=true` trong `backend/.env` và `VITE_ENABLE_DEMO_LOGIN=true` trong `frontend/.env.local`. Không bật `ENABLE_DEMO_LOGIN` trong môi trường production.

## Các lệnh hỗ trợ phát triển

Dự án tích hợp sẵn `Makefile` để rút gọn các thao tác thường ngày:

| Lệnh | Mô tả |
|---|---|
| `make install` | Cài đặt toàn bộ thư viện cho Backend và Frontend |
| `make dev-backend` | Chạy máy chủ phát triển Backend |
| `make dev-frontend` | Chạy máy chủ phát triển Frontend |
| `make test` | Chạy bộ kiểm thử tự động với Pytest |
| `make lint` | Kiểm tra quy chuẩn mã nguồn (Ruff & Oxlint) |
| `make lint-fix` | Tự động định dạng mã nguồn và sửa lỗi lint |
| `make migration msg="mô tả"` | Tự động sinh file migration mới từ thay đổi model |
| `make migrate` | Áp dụng các bản migration mới nhất vào cơ sở dữ liệu |

## Môi trường Staging

Hệ thống được thiết lập cơ chế triển khai liên tục (Continuous Deployment). Khi mã nguồn được gộp (merge) vào nhánh `main`, dịch vụ đám mây sẽ tự động cập nhật phiên bản mới nhất:

- **Web Staging:** https://ttcs-frontend-staging.onrender.com
- **API Staging:** https://ttcs-backend-staging.onrender.com/docs

Staging bật chế độ demo có chủ đích để phục vụ kiểm thử. Endpoint demo chỉ chấp nhận các tài khoản nằm trong allowlist và vẫn phát hành session theo cơ chế phiên chung của hệ thống. Backend staging bootstrap một role `ttcs_app` có mật khẩu sinh tự động; migration/seed sử dụng credential quản trị riêng, còn request API chạy bằng `ttcs_app` để RLS không phụ thuộc vào quyền của database owner.

## Quy trình đóng góp

Vui lòng đọc kỹ các quy định về phân nhánh, đặt tên commit và tạo Pull Request tại [CONTRIBUTING.md](./CONTRIBUTING.md) trước khi bắt đầu làm việc.
