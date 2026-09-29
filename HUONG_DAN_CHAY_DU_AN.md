# 🚀 HƯỚNG DẪN CHẠY DỰ ÁN CHO THÀNH VIÊN MỚI (N3-1)
> **Dành cho:** Tất cả thành viên Nhóm 3 — TTCS (Truy xuất nguồn gốc & Chuỗi lạnh nông sản)  
> **Mục tiêu:** Giúp mọi người tải code về và chạy thành công ứng dụng trên máy cá nhân.

---

## ⚡ CÁCH 1: KHỞI CHẠY BẰNG 1 LỆNH DOCKER (Khuyên dùng khi demo / nghiệm thu)

Nếu máy bạn đã cài sẵn **Docker Desktop**, bạn chỉ cần mở terminal tại thư mục dự án và chạy duy nhất **1 lệnh**:

```bash
docker compose up --build -d
```

Toàn bộ hệ thống sẽ tự động khởi động:
- 🔌 **Backend API:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- 🌐 **Frontend Web:** [http://localhost:5173](http://localhost:5173)
- 🗄️ **Database PostgreSQL:** Cổng `5432` (Database `ttcs_db`, User `admin`)

*Dừng ứng dụng khi không dùng nữa:*
```bash
docker compose down
```

---

## 💻 CÁCH 2: CHẠY TRỰC TIẾP (Dành cho máy không cài Docker hoặc lúc code hàng ngày)

Nếu bạn không dùng Docker, hãy làm theo các bước truyền thống dưới đây:

Nếu máy bạn chưa có các công cụ này, hãy tải và cài đặt theo link:

1. **Git:** [Tải Git tại đây](https://git-scm.com/download/win) *(Cứ bấm Next liên tục khi cài đặt)*
2. **Python (3.11 trở lên):** [Tải Python tại đây](https://www.python.org/downloads/)  
   ⚠️ **CỰC KỲ QUAN TRỌNG:** Khi cài Python nhớ tích vào ô vuông **"Add Python to PATH"**.
3. **Node.js (Bản LTS):** [Tải Node.js tại đây](https://nodejs.org/)
4. **Visual Studio Code:** [Tải VS Code tại đây](https://code.visualstudio.com/)

---

## 📥 PHẦN 2: Tải dự án về máy (Git Clone)

Mở **Terminal** (hoặc PowerShell / Git Bash) trên máy tính của bạn và chạy:

```bash
# 1. Đi đến thư mục bạn muốn chứa code (ví dụ Desktop hoặc D:\Projects)
cd Desktop

# 2. Clone mã nguồn về máy
git clone https://github.com/nhom-3-cnttk23c/truy-xuat-nguon-goc-chuoi-lanh-nong-san.git

# 3. Đi vào thư mục dự án vừa tải
cd truy-xuat-nguon-goc-chuoi-lanh-nong-san
```

---

## ⚙️ PHẦN 3: Khởi chạy Backend (API Server)

Mở thư mục dự án bằng **VS Code**, sau đó mở 1 cửa sổ **Terminal mới** (`Ctrl + ` `~`) và chạy lần lượt các lệnh:

```bash
# 1. Di chuyển vào thư mục backend
cd backend

# 2. Tạo môi trường ảo Python (Virtual Environment)
python -m venv .venv

# 3. Kích hoạt môi trường ảo
# Trên Windows (PowerShell / CMD):
.venv\Scripts\activate
# (Nếu dùng macOS / Linux: source .venv/bin/activate)

# 4. Cài đặt các thư viện cần thiết
pip install -r requirements.txt

# 5. Khởi chạy Server Backend
uvicorn app.main:app --reload
```

### ✅ Kết quả thành công:
Màn hình terminal hiện thông báo: `Application startup complete. Uvicorn running on http://127.0.0.1:8000`  
👉 Mở trình duyệt web truy cập: [http://localhost:8000/docs](http://localhost:8000/docs)  
*(Nếu thấy trang tài liệu Swagger API hiện lên là bạn đã chạy Backend thành công!)*

---

## 🎨 PHẦN 4: Khởi chạy Frontend (Giao diện người dùng)

Trong VS Code, bấm dấu **`+`** ở góc phải khu vực Terminal để **mở thêm 1 cửa sổ Terminal thứ hai** (giữ cửa sổ Backend vẫn đang chạy nhé), sau đó gõ:

```bash
# 1. Di chuyển vào thư mục frontend
cd frontend

# 2. Cài đặt các gói thư viện Node
npm install

# 3. Khởi chạy Server Frontend
npm run dev
```

### ✅ Kết quả thành công:
Màn hình terminal hiện: `Local: http://localhost:5173/`  
👉 Mở trình duyệt web truy cập: [http://localhost:5173](http://localhost:5173)  
*(Nếu thấy giao diện website React/Vite hiện lên là bạn đã chạy Frontend thành công!)*

---

## 📋 PHẦN 5: Checklist nghiệm thu Task N3-1

Bạn đã hoàn thành 100% Task N3-1 khi đạt đủ 3 điều kiện sau:
- [x] Clone repo về máy thành công không báo lỗi.
- [x] Backend chạy ở port `8000` (xem được trang Swagger: `http://localhost:8000/docs`).
- [x] Frontend chạy ở port `5173` (xem được giao diện: `http://localhost:5173`).

---

## ❓ Xử lý một số lỗi thường gặp (Troubleshooting)

### 1. Lỗi PowerShell chặn chạy script (`activate : File cannot be loaded because running scripts is disabled...`)
* **Cách sửa:** Mở PowerShell với quyền Administrator (Run as Administrator) và gõ lệnh sau rồi gõ `Y`:
  ```powershell
  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### 2. Lỗi `python` hoặc `npm` không được nhận dạng (`is not recognized as an internal or external command`)
* **Cách sửa:** Bạn chưa tích chọn "Add to PATH" lúc cài Python/Node.js. Hãy cài lại và nhớ tích chọn ô này, sau đó khởi động lại VS Code.

### 3. Cổng 8000 hoặc 5173 bị trùng/chiếm dụng
* **Cách sửa:** Đổi port backend lúc chạy: `uvicorn app.main:app --reload --port 8001`
