# AgroChain — Hệ thống Truy xuất Nguồn gốc & Giám sát Chuỗi lạnh Nông sản

> Đồ án môn học: Thực tập cơ sở (TTCS) — Nhóm 3 CNTT K23C  
> Môi trường Staging: [Frontend](https://ttcs-frontend-staging.onrender.com) | [API Docs (Swagger)](https://ttcs-backend-staging.onrender.com/docs)

Hệ thống quản lý quy trình chuỗi lạnh nông sản từ vùng trồng đến phân phối: theo dõi lô hàng, ghi nhật ký telemetry (nhiệt độ, độ ẩm, GPS) theo cơ chế bất biến và phân quyền đa tổ chức.

---

## 1. Phân hệ Kỹ thuật Cốt lõi

| Mã phân hệ | Nghiệp vụ | Giải pháp kỹ thuật | Trạng thái |
|---|---|---|---|
| **N3-4** | Toàn vẹn dữ liệu chuỗi lạnh | Băm SHA-256 nối chuỗi + chuẩn hóa Canonical JSON RFC 8785 | Đạt kiểm thử |
| **N3-5** | Quản lý xác thực & phiên | Argon2id + Cookie HttpOnly (`__Host-session`, SameSite=None, Secure) | Đạt kiểm thử |
| **N3-6** | Phân quyền & Đa tổ chức | PostgreSQL FORCE Row Level Security (RLS) + RBAC | Đạt kiểm thử |
| **N3-7** | Danh mục vùng trồng | Tọa độ GPS chuẩn WGS84, mã định danh UUID v4 | Đạt kiểm thử |
| **N3-21** | Bất biến nhật ký sự kiện | Trigger PostgreSQL chặn mọi thao tác UPDATE/DELETE | Đạt kiểm thử |

---

## 2. Tài khoản Thử nghiệm (Demo Accounts)

Hệ thống được khởi tạo sẵn dữ liệu mẫu cho 3 vai trò nghiệp vụ. Mật khẩu mặc định cho toàn bộ tài khoản mẫu là: `Password123!`

| Vai trò | Email đăng nhập | Mật khẩu | Phạm vi quyền hạn |
|---|---|---|---|
| **Nông hộ (Grower)** | `grower@caudat.vn` | `Password123!` | Quản lý nông trại Cầu Đất, tạo lô hàng, ghi nhật ký chuỗi lạnh |
| **Quản trị HTX (Admin)** | `admin@mocchau.vn` | `Password123!` | Quản lý hợp tác xã Mộc Châu, phân quyền thành viên và vùng trồng |
| **Thanh tra viên (Inspector)** | `inspector@chicuc.gov.vn` | `Password123!` | Đọc dữ liệu toàn hệ thống, kiểm tra chéo tính toàn vẹn chuỗi sự kiện |

*Cơ chế chống brute-force: Nhập sai mật khẩu 5 lần liên tiếp sẽ bị khóa phiên tạm thời 15 phút.*

---

## 3. Công nghệ Sử dụng

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16 (`psycopg3`).
- **Frontend:** React 19, TypeScript, Vite, Vanilla CSS.
- **Kiểm thử & Linter:** Pytest (Async/ASGITransport), Ruff, Oxlint.
- **Hạ tầng:** Docker, Docker Compose, Render (Web Service + Static Site + Managed PostgreSQL), GitHub Actions CI/CD.

---

## 4. Cấu trúc Dự án

```text
.
├── backend/
│   ├── alembic/             # Quản lý phiên bản migration cơ sở dữ liệu
│   ├── app/
│   │   ├── api/v1/          # Endpoints: auth, farms, lots, events
│   │   ├── core/            # Config, database engine, auth, crypto
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic schemas (validation & serialization)
│   │   ├── services/        # Nghiệp vụ băm, tính toàn vẹn chuỗi sự kiện
│   │   ├── main.py          # Khởi tạo ứng dụng FastAPI & cấu hình CORS
│   │   └── startup.py       # Bootstrap quyền database và nâng cấp migration
│   └── tests/               # Kiểm thử tự động (Pytest)
├── frontend/
│   ├── src/
│   │   ├── components/      # LoginView, FarmWorkspace, LotsPanel, EventTimeline
│   │   ├── services/api.ts  # Tầng kết nối REST API & quản lý phiên
│   │   ├── types/           # Định nghĩa Type TypeScript
│   │   ├── App.tsx          # Điều hướng & đồng bộ phiên
│   │   └── index.css        # Hệ thống thiết kế giao diện
│   └── vite.config.ts       # Cấu hình Vite & reverse proxy dev
├── docs/                    # Tài liệu đặc tả kỹ thuật (API, RLS, tính toàn vẹn)
├── docker-compose.yml       # Cấu hình container khởi chạy toàn bộ dịch vụ
└── Makefile                 # Tập hợp các lệnh tắt phục vụ phát triển
```

---

## 5. Hướng dẫn Khởi chạy

### Cách 1: Khởi chạy bằng Docker Compose (Khuyên dùng)

Yêu cầu máy đã cài và bật Docker Desktop:

```bash
# 1. Sao chép file cấu hình môi trường
cp .env.example .env

# 2. Khởi chạy toàn bộ hệ thống (PostgreSQL + Backend + Frontend)
docker compose up --build -d
```

Sau khi khởi động hoàn tất:
- **Giao diện Web:** [http://localhost:5173](http://localhost:5173)
- **Tài liệu API (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Dừng dịch vụ:** `docker compose down`

---

### Cách 2: Khởi chạy trực tiếp trên máy (Local Development)

#### 1. Backend (FastAPI)
Yêu cầu Python 3.12+ và PostgreSQL 16:

```bash
cd backend

# Khởi tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường ảo:
# Windows (cmd/PowerShell):
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Cài đặt thư viện phát triển
pip install -r requirements-dev.txt

# Cấu hình biến môi trường
cp .env.example .env
# Cập nhật DB_PASSWORD và DB_ADMIN_PASSWORD trong file .env cho khớp máy cục bộ

# Chạy migration và khởi động server
python -m app.startup
```

#### 2. Frontend (React + Vite)
Mở một cửa sổ terminal mới:

```bash
cd frontend

# Cài đặt thư viện
npm install

# Chạy máy chủ phát triển
npm run dev
```

*Lưu ý về Dev Proxy:* Khi chạy `npm run dev`, Vite được cấu hình proxy ngầm các yêu cầu `/api` sang Backend Staging (hoặc Backend local nếu đặt biến `VITE_BACKEND_TARGET`). Do đó, bạn có thể kiểm thử toàn bộ giao diện và chức năng đăng nhập ngay cả khi chưa bật PostgreSQL cục bộ.

---

## 6. Lệnh Thường dùng (Makefile)

Nếu môi trường hỗ trợ `make`:

| Lệnh | Mục đích |
|---|---|
| `make install` | Cài đặt dependencies cho cả Backend và Frontend |
| `make dev-backend` | Khởi chạy máy chủ Backend (FastAPI) |
| `make dev-frontend` | Khởi chạy máy chủ Frontend (Vite) |
| `make test` | Chạy bộ kiểm thử tự động với Pytest |
| `make lint` | Kiểm tra quy chuẩn mã nguồn (Ruff & Oxlint) |
| `make lint-fix` | Tự động định dạng và sửa lỗi lint |
| `make migrate` | Áp dụng bản migration mới nhất vào cơ sở dữ liệu |

---

## 7. Kiến trúc An toàn Dữ liệu

1. **Cô lập Đa tổ chức (PostgreSQL RLS):** Cơ chế Row Level Security được kích hoạt với mức nghiêm ngặt (`FORCE ROW LEVEL SECURITY`). Tầng ứng dụng derive tenant trực tiếp từ session hash trong transaction context, ngăn chặn triệt để nguy cơ giả mạo tổ chức từ tham số request.
2. **Nhật ký Sự kiện Bất biến (N3-21):** Bảng `events` chỉ cấp quyền `SELECT` và `INSERT` cho app role. Hai database trigger `trg_events_prevent_update` và `trg_events_prevent_delete` chặn đứng mọi nỗ lực can thiệp hoặc sửa đổi dữ liệu đã ghi.
3. **Quản lý Phiên (N3-5):** Phiên làm việc sử dụng cookie `__Host-session` với cờ `HttpOnly`, `Secure` và `SameSite=None`. Mã phiên không bao giờ xuất hiện trong response body hay Web Storage (`localStorage`), ngăn ngừa tấn công XSS đánh cắp phiên.

---

## 8. Quy trình Đóng góp

Vui lòng tham khảo [CONTRIBUTING.md](./CONTRIBUTING.md) để tuân thủ quy định về phân nhánh, đặt tên commit theo chuẩn Conventional Commits và tạo Pull Request.
