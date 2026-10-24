# Quy chuẩn Đóng góp và Làm việc Nhóm

Tài liệu này quy định quy trình quản lý mã nguồn, tiêu chuẩn chất lượng và cách thức phối hợp giữa các thành viên trong dự án **VietFarm Trace (AgroChain)**.

Tài liệu liên quan:

- [Definition of Done và Definition of Ready](docs/DOD-DOR.md) — điều kiện trước khi nhận việc và trước khi chuyển trạng thái hoàn thành.
- [Cách dùng Jira của nhóm](docs/JIRA-GUIDE.md) — cách cập nhật bình luận, chuyển trạng thái và vai trò từng thành viên.
- [Vận hành hệ thống](docs/OPERATIONS.md) — kiểm tra sau triển khai, job bảo trì và cấu hình hạ tầng staging.

## 1. Quy trình quản lý nhánh (Git Branching)

Nhánh `main` là nhánh chính thức, luôn đảm bảo trạng thái ổn định và đã được bảo vệ. Thành viên phát triển trên nhánh tính năng hoặc nhánh tích hợp (`develops`) và gửi Pull Request theo định dạng:

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
     ruff check app tests alembic
     ruff format --check app tests alembic
     pytest tests/ -v
     ```
   - **Frontend:**
     ```bash
     cd frontend
     npm test
     npm run lint
     npm run build
     ```

4. **Đẩy nhánh lên kho lưu trữ và tạo Pull Request:**
   ```bash
   git push origin feature/ten-tinh-nang
   ```

## 4. Quy định về Pull Request (PR) và CI/CD

- **Mô tả rõ ràng:** Khi mở PR, ghi rõ mục tiêu thay đổi, các phần bị ảnh hưởng và cách thức kiểm tra.
- **Kiểm tra tự động (CI):** Hệ thống GitHub Actions tự động chạy kiểm tra cú pháp (lint), kiểm thử (unit/integration test), kiểm tra migration, quét lỗ hổng thư viện và đóng gói Docker. PR chỉ được gộp khi toàn bộ các bước kiểm tra đều vượt qua.
- **Đánh giá chéo (Code Review):** Mỗi PR cần tối thiểu 1 thành viên khác trong nhóm kiểm tra và phê duyệt (Approve) trước khi gộp vào `main`.

## 5. Tổ chức mã nguồn và Nguyên tắc thiết kế

### Backend (`backend/app/`)
- **`api/v1/endpoints/`:** Tiếp nhận HTTP request, kiểm tra quyền và trả về response theo schema chuẩn.
- **`services/`:** Nơi xử lý toàn bộ nghiệp vụ của ứng dụng (lô hàng, phả hệ, chuỗi băm sự kiện, chuỗi lạnh, thu hồi, báo cáo PDF, ẩn danh PII).
- **`models/`:** Định nghĩa cấu trúc bảng cơ sở dữ liệu (SQLAlchemy). Mọi thay đổi trong thư mục này bắt buộc phải đi kèm tệp migration trong `backend/alembic/versions/`.
- **`schemas/`:** Định nghĩa cấu trúc dữ liệu đầu vào và đầu ra (Pydantic v2).
- **`jobs/`:** Các tác vụ bảo trì định kỳ chạy nền (đánh dấu bàn giao quá hạn, quét toàn vẹn chuỗi băm, nén dữ liệu nhiệt độ).

### Frontend (`frontend/src/`)
- **`components/`:** Các phân hệ giao diện và thành phần dùng chung của ứng dụng (`DashboardHomePanel`, `LotsDataTablePanel`, `LotDetailDrawer`, `ColdChainPanel`, `RecallsPanel`, `PublicTracePage`, `QrLabelModal`, `IntegrityTamperSimulatorModal`, v.v.).
- **`services/api.ts`:** Tập trung toàn bộ các hàm gọi HTTP API tới Backend kèm cơ chế làm mới phiên và đồng bộ dữ liệu. Không gọi `fetch` trực tiếp bên trong các component giao diện.
- **`types/`:** Khai báo đầy đủ kiểu dữ liệu TypeScript khớp với hợp đồng OpenAPI của Backend.
- **`utils/`:** Các hàm tiện ích định dạng ngày giờ, nhãn trạng thái tiếng Việt, tạo mã QR và kiểm tra hợp lệ dữ liệu.
