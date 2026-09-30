# Backend API

Base URL local: `http://localhost:8000/api/v1`. Interactive OpenAPI: `/docs`.

## Phiên đăng nhập và quyền

- `POST /auth/login` nhận `email`, `password`; trả thông tin người dùng và đặt cookie phiên `HttpOnly`.
- `GET /auth/me` trả người dùng hiện tại. `POST /auth/logout` thu hồi phiên.
- Phiên là **cookie `HttpOnly`** duy nhất. Token phiên không bao giờ được trả trong header
  (`X-Session-Token` đã bị loại bỏ) và không đọc được bằng JavaScript; server chỉ lưu SHA-256 của token.
- Cookie dùng tiền tố `__Host-` nên bắt buộc `Secure`, `Path=/` và không có `Domain`.
  Chỉ đặt `SESSION_COOKIE_SECURE=false` khi chạy local qua HTTP; mọi môi trường khác bị từ chối khởi động.
- Sai email, sai mật khẩu, tài khoản bị khóa hoặc bị vô hiệu đều trả cùng `401` với cùng thông báo.
- Sau `MAX_FAILED_LOGIN_ATTEMPTS` (mặc định 5) lần sai, tài khoản bị khóa `ACCOUNT_LOCK_MINUTES` (mặc định 15) phút.
  Trong lúc khóa, mật khẩu đúng vẫn bị từ chối. Hết thời gian khóa, đăng nhập lại được và bộ đếm được reset.
- API nghiệp vụ yêu cầu đăng nhập. Tổ chức được lấy từ phiên, không nhận `organization_id` do client tự khai báo;
  body gửi thêm `organization_id` bị từ chối (`422`).
- Mọi route nghiệp vụ dưới `/api/v1` phải khai báo `@require_permission`; route quên khai báo bị từ chối `403`
  (fail closed) kèm security log `authorization.route_missing_permission`.
- Danh sách dùng `page` (mặc định 1), `page_size` (mặc định 25, tối đa 100); phản hồi gồm `items`, `page`, `page_size`, `total`. Danh sách farms giữ dạng array để tương thích client cũ, với `limit` tối đa 100 và `offset`.

## Tổ chức và tài khoản

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| `GET` | `/organizations` | `system_admin` | Danh sách tổ chức có phân trang |
| `POST` | `/organizations` | `system_admin` | Tạo tổ chức và tài khoản quản trị đầu tiên trong cùng transaction |
| `GET` | `/users` | `organization_admin`, `system_admin` | Danh sách người dùng trong tổ chức hiện tại |
| `POST` | `/users` | `organization_admin`, `system_admin` | Tạo tài khoản trong tổ chức hiện tại; role bị giới hạn theo loại tổ chức |
| `PATCH` | `/users/{user_id}/active` | `organization_admin`, `system_admin` | Kích hoạt hoặc khóa người dùng cùng tổ chức |

## Farm và danh mục

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| `GET` | `/farms/` | grower, organization admin | Liệt kê farms của tổ chức, `limit`/`offset` |
| `POST` | `/farms/` | grower, organization admin | Tạo farm; `organization_id` lấy từ phiên |
| `GET` | `/farms/{farm_id}` | grower, organization admin | Chi tiết farm cùng tổ chức |
| `PATCH` | `/farms/{farm_id}` | grower, organization admin | Cập nhật một phần, dùng để **đổi tên**; `id` và `organization_id` không đổi nên lô đã gắn vẫn trỏ đúng thửa |
| `PUT` | `/farms/{farm_id}` | grower, organization admin | Thay thế toàn bộ 4 trường |
| `GET` | `/products/` | grower, cooperative, transporter, distributor, inspector, organization admin | Danh mục riêng của tổ chức |
| `POST` | `/products/` | grower, cooperative, distributor | Tạo sản phẩm và khoảng nhiệt độ cho phép |
| `GET` | `/products/{product_id}` | các role có `products:read` | Chi tiết sản phẩm cùng tổ chức |
| `PUT` | `/products/{product_id}` | grower, cooperative, distributor | Cập nhật sản phẩm và ngưỡng nhiệt độ |

Ràng buộc của farm được kiểm tra ở **hai lớp**: Pydantic (trả `422` kèm thông báo) và ràng buộc
`ck_farms_area_positive`, `ck_farms_latitude_range`, `ck_farms_longitude_range` ở PostgreSQL.
Tọa độ lưu `NUMERIC(9,6)` (khoảng 11 cm) và chỉ nhận `latitude ∈ [-90, 90]`, `longitude ∈ [-180, 180]`.

Truy cập chéo tổ chức trả `403` kèm security log `authorization.cross_organization_access`;
bản ghi không tồn tại trả `404`.

## Lô và truy xuất

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| `GET` | `/lots/` | các role có `lots:read` | Danh sách có lọc `status` và phân trang; inspector xem toàn hệ thống |
| `POST` | `/lots/` | grower, cooperative, distributor | Tạo lô gắn với sản phẩm và farm cùng tổ chức |
| `GET` | `/lots/{lot_id}` | các role có `lots:read` | Chi tiết lô trong phạm vi được cấp |
| `POST` | `/lots/{lot_id}/events` | grower, cooperative, distributor | Ghi nhận thu hoạch, sơ chế, đóng gói, lưu kho, kiểm định, bán hoặc hủy |
| `GET` | `/lots/{lot_id}/events` | các role có `lots:read` | Lịch sử có phân trang |
| `POST` | `/lots/derive` | grower, cooperative, distributor | Tạo lô mới qua split/merge, kèm số lượng phân bổ từ từng lô nguồn |
| `GET` | `/lots/{lot_id}/lineage` | các role có `lots:read` | Các quan hệ lô nguồn/lô đích |
| `GET` | `/trace/{public_code}` | công khai | Trang dữ liệu QR; chỉ trả trường công khai và tối đa 50 sự kiện mỗi lô trong chuỗi nguồn |

Các sự kiện chuyển trạng thái theo thứ tự `created → harvested → processed → packed → in_transit → received → stored → sold`. `inspection` không đổi trạng thái; `discarded` kết thúc lô. `received` chỉ được tạo qua xác nhận chuyến hàng.

## Vận chuyển và chuỗi lạnh

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| `GET` | `/shipments/` | các role có `shipments:read` | Chuyến hàng bên gửi/bên nhận; có lọc `status` và phân trang |
| `POST` | `/shipments/` | grower, cooperative, transporter, distributor | Chuyển giao toàn bộ một lô cho tổ chức nhận |
| `GET` | `/shipments/{shipment_id}` | bên gửi, bên nhận, inspector | Chi tiết chuyến hàng |
| `POST` | `/shipments/{shipment_id}/receive` | các role có `shipments:receive` | Nhận lô, cập nhật chủ sở hữu và ghi sự kiện trong một transaction |
| `GET` | `/shipments/{shipment_id}/readings` | bên gửi, bên nhận, inspector | Số đo cảm biến có phân trang |
| `POST` | `/sensors` | grower, transporter | Đăng ký cảm biến cho chuyến đang đi |
| `GET` | `/sensors` | transporter, inspector | Danh sách cảm biến có phân trang |
| `POST` | `/sensors/{sensor_id}/readings` | grower, transporter | Gửi batch 1–500 số đo; `source_reading_id` chống ghi lặp |
| `GET` | `/alerts` | grower, transporter, distributor, inspector | Cảnh báo nhiệt độ có lọc `status` và phân trang |
| `POST` | `/alerts/{alert_id}/resolve` | grower, transporter | Đóng cảnh báo trong tổ chức sở hữu |

## Vận hành

- `GET /` và `GET /health/live` kiểm tra tiến trình.
- `GET /health/ready` kiểm tra kết nối PostgreSQL.
- Endpoint mẫu `/items/` đã bị gỡ khỏi ứng dụng: nó từng được mount công khai dưới `/api/v1` mà không
  qua `enforce_route_permission`.
- `/docs`, `/redoc`, `/openapi.json` chỉ được bật khi `APP_ENV=development`.
- Mọi phản hồi kèm `X-Request-ID`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer` và `Cache-Control: no-store`.
- Security log dạng JSON trên logger `app.security`, ví dụ:
  `auth.login_succeeded`, `auth.login_failed`, `auth.logout`, `auth.session_expired`,
  `authorization.route_missing_permission`, `authorization.permission_denied`,
  `authorization.cross_organization_access`.
