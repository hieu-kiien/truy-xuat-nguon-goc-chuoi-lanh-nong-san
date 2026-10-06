# Hệ thống Truy xuất Nguồn gốc và Giám sát Chuỗi lạnh Nông sản

Ứng dụng quản lý vùng trồng, lô nông sản, bàn giao giữa các đơn vị và lịch sử truy xuất.

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

## Quy tắc nhật ký sự kiện

Sự kiện đã ghi nhận là append-only: API và vai trò ứng dụng trong cơ sở dữ liệu không được cập nhật hoặc xóa sự kiện. Khi cần sửa thông tin nghiệp vụ, hãy ghi thêm sự kiện mới để giữ lại lịch sử. Mã băm liên kết sự kiện với nội dung chuẩn hóa theo RFC 8785; dùng `GET /api/v1/events/lots/{lot_id}/integrity` để kiểm tra chuỗi.

## Hướng dẫn cài đặt và khởi chạy

### 1. Khởi chạy nhanh bằng Docker Compose

Yêu cầu máy tính đã cài đặt và bật **Docker Desktop**. Chạy lệnh sau tại thư mục gốc của dự án:

```bash
cp .env.example .env
# Set unique local values for DB_PASSWORD, DB_ADMIN_PASSWORD, and DEMO_PASSWORD.
docker compose up --build -d
```

Sau khi các container khởi động hoàn tất:
- **Giao diện Web:** http://localhost:5173
- **Tài liệu API (Swagger UI):** http://localhost:8000/docs
- **Cơ sở dữ liệu PostgreSQL:** `localhost:5432` (database: `ttcs_db`)

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
# Set DB_PASSWORD and DB_ADMIN_PASSWORD to different local secrets.
python -m app.startup
```

#### Frontend (React + Vite)

Mở một cửa sổ terminal mới:

```bash
cd frontend
npm install
cp .env.example .env.local

npm run dev
```

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

Staging creates the application database role at startup and runs migrations
with the separate migration role. Demo accounts are seeded only for local
development when DEMO_PASSWORD is configured.

## Quy trình đóng góp

Vui lòng đọc kỹ các quy định về phân nhánh, đặt tên commit và tạo Pull Request tại [CONTRIBUTING.md](./CONTRIBUTING.md) trước khi bắt đầu làm việc.
