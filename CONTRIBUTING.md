# Quy chuẩn Đóng góp và Làm việc Nhóm

Tài liệu này quy định quy trình quản lý mã nguồn, tiêu chuẩn chất lượng và cách thức phối hợp giữa các thành viên trong dự án.

## 1. Quy trình quản lý nhánh (Git Branching)

Nhánh `main` là nhánh chính thức, luôn đảm bảo trạng thái ổn định và đã được bảo vệ. Thành viên không đẩy (push) trực tiếp mã nguồn lên `main` mà thực hiện qua nhánh riêng theo định dạng:

```text
<loại-nhánh>/<mô-tả-ngắn-gọn>
```

| Tiền tố | Mục đích | Ví dụ |
|---|---|---|
| `feature/` | Phát triển tính năng mới | `feature/auth-login`, `feature/farm-declaration` |
| `fix/` | Sửa lỗi phát sinh | `fix/cors-headers`, `fix/sensor-timeout` |
| `refactor/` | Tái cấu trúc mã nguồn, không đổi tính năng | `refactor/user-service` |
| `docs/` | Cập nhật tài liệu kỹ thuật | `docs/api-specification` |
| `chore/` | Cập nhật cấu hình, thư viện phụ thuộc | `chore/upgrade-dependencies` |

*Lưu ý: Tên nhánh viết thường, không dấu, các từ nối với nhau bằng dấu gạch ngang (`-`). Không đặt tên nhánh theo tên cá nhân.*

## 2. Quy chuẩn Commit Message

Mỗi commit cần thể hiện rõ phạm vi thay đổi theo cấu trúc:

```text
<type>: <mô tả ngắn gọn nội dung thay đổi>
```

Ví dụ:
- `feat: thêm api khai báo vùng trồng và thửa đất`
- `fix: xử lý lỗi kết nối cơ sở dữ liệu khi khởi động`
- `test: bổ sung kiểm thử cho chức năng đăng nhập`
- `refactor: tách xử lý truy vấn lô hàng sang tầng service`

## 3. Luồng làm việc tiêu chuẩn

1. **Đồng bộ mã nguồn mới nhất từ nhánh chính:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Tạo nhánh làm việc mới:**
   ```bash
   git checkout -b feature/ten-tinh-nang
   ```

3. **Kiểm tra chất lượng mã nguồn trước khi đẩy lên:**
   - **Backend:**
     ```bash
     cd backend
     ruff check --fix app/ tests/
     ruff format app/ tests/
     pytest tests/ -v
     ```
   - **Frontend:**
     ```bash
     cd frontend
     npm run lint
     npm run build
     ```

4. **Đẩy nhánh lên kho lưu trữ và tạo Pull Request:**
   ```bash
   git push origin feature/ten-tinh-nang
   ```

## 4. Quy định về Pull Request (PR) và CI/CD

- **Mô tả rõ ràng:** Khi mở PR, ghi rõ mục tiêu thay đổi, các phần bị ảnh hưởng và cách thức kiểm tra.
- **Kiểm tra tự động (CI):** Hệ thống GitHub Actions sẽ tự động chạy kiểm tra cú pháp (lint), kiểm thử (unit test) và đóng gói Docker. PR chỉ có thể được gộp khi toàn bộ các bước kiểm tra đều vượt qua.
- **Đánh giá chéo (Code Review):** Mỗi PR cần tối thiểu 1 thành viên khác trong nhóm kiểm tra và phê duyệt (Approve) trước khi gộp vào `main`.

## 5. Tổ chức mã nguồn và Nguyên tắc thiết kế

### Backend (`backend/app/`)
- **`api/v1/endpoints/`:** Chỉ tiếp nhận HTTP request, kiểm tra quyền và trả về response. Không viết logic nghiệp vụ phức tạp hoặc truy vấn trực tiếp tại đây.
- **`services/`:** Nơi xử lý toàn bộ nghiệp vụ của ứng dụng.
- **`models/`:** Định nghĩa cấu trúc bảng cơ sở dữ liệu (SQLAlchemy). Mọi thay đổi trong thư mục này bắt buộc phải tạo file migration thông qua Alembic (`make migration msg="..."`).
- **`schemas/`:** Định nghĩa cấu trúc dữ liệu đầu vào và đầu ra (Pydantic).

### Frontend (`frontend/src/`)
- **`components/`:** Các thành phần giao diện dùng chung, thiết kế độc lập và tái sử dụng được.
- **`pages/`:** Các màn hình giao diện gắn với từng đường dẫn (route).
- **`services/api.ts`:** Tập trung toàn bộ các hàm gọi HTTP API tới Backend. Không gọi `fetch` trực tiếp bên trong các component giao diện.
- **`types/`:** Khai báo đầy đủ kiểu dữ liệu TypeScript, hạn chế tối đa việc sử dụng kiểu `any`.
