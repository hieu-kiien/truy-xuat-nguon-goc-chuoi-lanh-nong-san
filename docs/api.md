# API

Hợp đồng API hiện hành được sinh từ Pydantic/FastAPI tại `/openapi.json`; dùng `/docs` để xem và thử. Không duy trì thêm bảng endpoint bằng tay.

- Staging: https://ttcs-backend-staging.onrender.com/docs
- Local: http://localhost:8000/docs
- Browser đăng nhập bằng cookie HttpOnly, Secure, SameSite=None; không lưu session token vào localStorage.
- Các route nghiệp vụ dưới `/api/v1` kiểm quyền ở máy chủ; dữ liệu ngoài phạm vi được từ chối.
- `GET /health` kiểm readiness, không yêu cầu đăng nhập. `GET /version` chỉ trả commit SHA.
- Danh sách lô dùng cursor, mặc định UI 20 dòng, lọc theo sản phẩm và tìm mã không phân biệt hoa/thường.
- Lịch sử `/api/v1/events/lots/{lot_id}/history` nhận `after` (sequence) và `page_size` (1–500). Trả `events`, `next_cursor`, `total`, `integrity`. Toàn bộ chuỗi có quyền xem vẫn được kiểm tra, kể cả khi trang chỉ chứa 10 sự kiện.
- Chi tiết lô trả `root_farms` để tổng quan hiển thị nguồn gốc; dữ liệu logistics của lô lịch sử bị ẩn.
- Sự kiện không có route sửa/xóa. Các sự kiện hệ thống chỉ được tạo qua thao tác nghiệp vụ tương ứng.
- **Ngưỡng chuỗi lạnh theo loại sản phẩm (N3-62):** `PUT /api/v1/products/{product_id}/cold-chain-config` (quyền `products:write`, chỉ quản trị hệ thống) đặt `min_temp_celsius`, `max_temp_celsius`, `delay_minutes`; `GET` cùng đường dẫn (`products:read`) đọc cấu hình hiện tại, trả 404 khi chưa cấu hình. Khi mở chuyến, hệ thống chốt (snapshot) ngưỡng chặt nhất của mọi loại hàng lên chuyến — ngưỡng dưới lớn nhất, ngưỡng trên nhỏ nhất, độ trễ ngắn nhất; sản phẩm chưa cấu hình dùng mặc định 2–8°C, 30 phút. Mỗi lần nạp số đo và tính vi phạm dùng đúng snapshot đó; đổi cấu hình về sau không tính lại vi phạm của chuyến đang chạy. `GET /api/v1/telemetry/shipments/{id}/cold-chain-limits` xem ngưỡng hiệu lực kèm nguồn theo từng loại; phản hồi nạp số đo kèm `applied_limits`.
- **Lệnh thu hồi (S-38/N3-55):** `POST /api/v1/recalls` (quyền `recalls:manage`) tạo lệnh với `code`, `lot_ids[]`; `POST /api/v1/recalls/{id}/complete` đóng lệnh; `PATCH /api/v1/recalls/{id}/lots/{lot_id}` bật/tắt cờ sự cố. Lô thuộc lệnh `open` hoặc lệnh `completed` mà cờ sự cố vẫn `true` bị chặn bàn giao, tách, gộp với mã 409 kèm mã lệnh thu hồi.
