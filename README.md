# Dự án TTCS — N3

Ứng dụng web với kiến trúc phân tách Frontend/Backend:
- **Backend:** Python + FastAPI
- **Frontend:** React + Vite + TypeScript

## Cấu trúc dự án
```
ttcs_n3/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   ← Các route API
│   │   ├── core/               ← Config, database
│   │   ├── models/             ← SQLAlchemy models
│   │   ├── schemas/            ← Pydantic schemas
│   │   ├── services/           ← Business logic
│   │   └── main.py             ← Điểm khởi chạy
│   ├── tests/                  ← Unit & Integration tests
│   ├── requirements.txt        ← Thư viện Python
│   ├── .python-version         ← Phiên bản Python (3.14)
│   └── .env.example            ← Mẫu biến môi trường
├── frontend/
│   ├── src/                    ← Mã nguồn React
│   ├── package.json
│   ├── .nvmrc                  ← Phiên bản Node.js (24)
│   └── .env.example            ← Mẫu biến môi trường
├── docs/
│   └── api.md                  ← Tài liệu API cho cả nhóm
├── .gitignore
└── README.md
```

## Cài đặt môi trường (làm 1 lần)

| Công cụ | Phiên bản | Link |
|---|---|---|
| Python | 3.14 | https://www.python.org/downloads/ |
| Node.js | 24 | https://nodejs.org |
| PostgreSQL | 15+ | https://www.postgresql.org/download/ |

## Chạy Backend

```bash
cd backend

# 1. Tạo môi trường ảo Python
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Cấu hình biến môi trường
cp .env.example .env
# Mở file .env và điền thông tin DB của bạn

# 4. Chạy server
uvicorn app.main:app --reload
```
API chạy tại: http://localhost:8000  
Tài liệu API tự động: http://localhost:8000/docs

## Chạy Frontend

```bash
cd frontend

# 1. Cài thư viện
npm install

# 2. Cấu hình biến môi trường
cp .env.example .env.local

# 3. Chạy ứng dụng
npm run dev
```
Giao diện tại: http://localhost:5173

## Git Workflow cho nhóm

```bash
git pull origin main          # Cập nhật code mới nhất
# ... code ...
git add .
git commit -m "feat: mô tả tính năng"
git push origin <tên-nhánh>
```
