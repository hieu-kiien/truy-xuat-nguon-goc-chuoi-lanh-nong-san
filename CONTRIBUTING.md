# 📜 Quy định đóng góp & Làm việc nhóm — TTCS N3

Tài liệu này là **luật làm việc chung** của dự án. Tất cả 10 thành viên nhóm đều phải đọc kỹ và tuân thủ để tránh xung đột mã nguồn (merge conflict) và đảm bảo chất lượng hệ thống.

---

## 1. Quy tắc đặt tên nhánh Git (Branching Convention)

- **Tuyệt đối không push code trực tiếp lên nhánh `main`.**
- Mỗi tính năng hoặc sửa lỗi phải được thực hiện trên một nhánh riêng biệt, đặt tên theo chuẩn:
  `<type>/<ma-task-hoac-ten-tinh-nang>`

| Tiền tố | Mục đích sử dụng | Ví dụ thực tế trong dự án |
|---|---|---|
| `feature/` | Phát triển tính năng mới | `feature/n3-5-login`, `feature/n3-7-khai-bao-dat` |
| `fix/` | Sửa lỗi phát sinh | `fix/db-connection-timeout`, `fix/cors-origin-issue` |
| `docs/` | Cập nhật tài liệu kỹ thuật | `docs/update-api-contract` |
| `refactor/` | Tối ưu hoặc cấu trúc lại mã nguồn | `refactor/clean-auth-service` |
| `chore/` | Cấu hình, nâng cấp thư viện | `chore/update-pydantic-config` |

> ❌ **Nghiêm cấm đặt tên nhánh:** `kien`, `nam-dev`, `test`, `fix1`, `nhanh-moi`

---

## 2. Quy tắc viết Commit Message

Format chuẩn: `<type>: <mô tả ngắn gọn bằng tiếng Việt>`

```text
feat: thêm api đăng nhập bằng email và mật khẩu (n3-5)
fix: sửa lỗi không nhận diện biến môi trường ALLOWED_ORIGINS
test: bổ sung unit test cho endpoint truy xuất nông sản
docs: cập nhật mô tả các api v1 trong docs/api.md
refactor: tách hàm tính toán nhiệt độ chuỗi lạnh sang service riêng
```

> ❌ **Không viết commit vô nghĩa:** `fix bug`, `update code`, `asdasd`, `done`

---

## 3. Quy trình làm việc hàng ngày (Workflow)

```text
              main (nhánh chính — luôn chạy ổn định)
                │
                ├── feature/n3-5-login       (Bạn A)
                ├── feature/n3-7-thua-dat    (Bạn B)
                └── fix/sensor-data-parsing  (Bạn C)
```

### Các bước thực hiện:

1. **Cập nhật code mới nhất từ `main` trước khi làm việc:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Tạo nhánh mới từ `main`:**
   ```bash
   git checkout -b feature/n3-5-login
   ```

3. **Lập trình và commit thường xuyên:**
   ```bash
   git add .
   git commit -m "feat: xay dung form dang nhap frontend"
   ```

4. **Kiểm tra chất lượng trước khi push (Tránh làm đỏ CI):**
   ```bash
   # Kiểm tra lint và test của Backend
   cd backend
   ruff check app/ tests/
   pytest tests/ -v

   # Kiểm tra build của Frontend
   cd ../frontend
   npm run build
   ```

5. **Đẩy nhánh lên GitHub:**
   ```bash
   git push origin feature/n3-5-login
   ```

6. **Mở Pull Request (PR) trên GitHub:**
   - Chọn nhánh đích là `main`.
   - Ghi rõ nội dung thay đổi, task liên quan trên Jira và cách kiểm thử.

---

## 4. Pipeline CI & Quy tắc xét duyệt (Task N3-2)

Dự án đã tích hợp sẵn **GitHub Actions CI**. Mỗi khi một PR được tạo:
* Hệ thống sẽ tự động chạy:
  1. 🐍 **Backend:** Ruff Linter + Pytest
  2. ⚛️ **Frontend:** Typecheck + Vite Build
  3. 🐳 **Docker:** Build thử Docker Images
* **Nếu có bất kỳ bước nào báo Đỏ ❌:** Nút **Merge sẽ bị khóa tự động**. Tác giả PR bắt buộc phải fix lỗi và push lại.
* **Quy tắc phê duyệt:** Mỗi PR cần ít nhất **1 thành viên khác review và Approve** mới được phép gộp vào `main`.

---

## 5. Cấu trúc mã nguồn — Đặt file ở đâu?

Để tránh xáo trộn cấu trúc dự án, mọi người tuân thủ vị trí lưu file:

### 🐍 Backend (`backend/app/`):
- `api/v1/endpoints/`: Định nghĩa các API routes mới (ví dụ: `auth.py`, `farms.py`, `sensors.py`).
- `models/`: Định nghĩa các bảng database bằng SQLAlchemy (ví dụ: `user.py`, `plot.py`).
- `schemas/`: Định nghĩa định dạng dữ liệu đầu vào / đầu ra bằng Pydantic (ví dụ: `user.py`).
- `services/`: Chứa các hàm xử lý logic nghiệp vụ phức tạp.
- `alembic/versions/`: Tạo migration tự động bằng lệnh `make migration msg="ten_thay_doi"`.

### ⚛️ Frontend (`frontend/src/`):
- `components/`: Chứa các thành phần giao diện nhỏ dùng lại (Navbar, Footer, Button, Card...).
- `pages/`: Chứa các màn hình hoàn chỉnh (LoginPage, FarmManagementPage, Dashboard...).
- `services/api.ts`: Nơi duy nhất gọi các API Backend (tuyệt đối không `fetch` trực tiếp trong component).
- `hooks/`: Chứa custom hooks xử lý dữ liệu chung (`useApi.ts`...).
- `types/`: Khai báo các interface / type TypeScript.
- `utils/`: Các hàm định dạng ngày tháng, số liệu tiện ích.
