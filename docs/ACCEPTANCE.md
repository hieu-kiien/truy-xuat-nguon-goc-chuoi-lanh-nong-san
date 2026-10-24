# Báo cáo Nghiệm thu Tổng hợp (Sprint 1 – Sprint 8)

Tài liệu này tổng hợp kết quả kiểm chứng mã nguồn, cơ sở dữ liệu, kiểm thử tự động và kiểm thử E2E trên môi trường thực tế cho toàn bộ phạm vi dự án **VietFarm Trace (AgroChain)** từ **Sprint 1 đến Sprint 8 (`N3-1` → `N3-160`)**.

---

## 1. Tổng quan Bằng chứng Kiểm chứng

| Hạng mục kiểm chứng | Kết quả đạt được |
|---|---|
| **Backend (Pytest Integration, RBAC/RLS, Lineage, Hash Chain, Cold Chain, Recalls, PDF, PII, Backup)** | Toàn bộ bộ kiểm thử tích hợp tại `backend/tests/` và 3 bài kiểm thử hiệu năng (`-m performance`) vượt qua 100%. |
| **Hiệu năng truy vấn (Performance Benchmarks)** | Lịch sử 200 sự kiện ~68 ms (với CTE `MATERIALIZED` quét bảng tổ chức đúng 1 lần); danh sách 5.000 lô ~76 ms (< 300 ms); đồ thị phả hệ 1.000 nút ~0,80 s xuôi / ~0,73 s ngược; tạo & kiểm chuỗi băm 1.000 sự kiện ~18,4 ms. |
| **Frontend (Unit, Contract & E2E Flow Tests)** | **73 / 73 bài kiểm thử tự động** (`npm test`) vượt qua 100%; `npm run lint` (0 lỗi, 0 cảnh báo) và `npm run build` (TypeScript + Vite production build) thành công. |
| **Hợp đồng API (OpenAPI 3.1)** | **69 đường dẫn API** (`38` nhóm hợp đồng nghiệp vụ cốt lõi được kiểm tra tự động trong workflow `deploy-staging.yml`). |
| **Lược đồ Cơ sở dữ liệu (Alembic Migrations)** | Chuỗi 44 bản nâng cấp liên tục đạt tới revision **`20261021_44`** (`alembic upgrade head` và kiểm tra hạ cấp/nâng cấp vòng lặp trên DB trống). |
| **Phân tách quyền Runtime & PostgreSQL RLS** | Ứng dụng web chạy bằng vai trò `agrochain_app` (không có `SUPERUSER` / `BYPASSRLS`), không giữ mật khẩu quản trị migration trong quá trình phục vụ HTTP. |
| **Diễn tập Sao lưu & Phục hồi (N3-76 / N3-160)** | 2 lần diễn tập thực tế (`2,288 s` và `2,214 s`), khớp `9/9` bảng nghiệp vụ, kiểm tra lại chuỗi băm toàn bộ lô đạt `broken_lots = 0` ([RESTORE-DRILLS.md](RESTORE-DRILLS.md)). |
| **Kiểm thử E2E trên miền triển khai thật (Live Staging)** | Đã kiểm chứng trực tiếp trên `https://ttcs-frontend-staging.onrender.com` và `https://ttcs-backend-staging.onrender.com` qua cả **6 vai trò** và **4 mã lô mẫu công khai** (`4S594256`, `P8V8RDPM`, `WJS2JKHZ`, `YEQTXCQ7`). |

---

## 2. Đối chiếu Nghiệm thu theo từng Giai đoạn (Sprint 1 – Sprint 8)

### Giai đoạn 1: Nền tảng Hạ tầng, Phân quyền RLS & Chuỗi băm (Sprint 1 – Sprint 4)

| Nhóm nhiệm vụ Jira | Nội dung triển khai & Kiểm chứng |
|---|---|
| `N3-1` / `N3-77` | Khởi động an toàn (`python -m app.startup`), dừng ngay khi thiếu biến môi trường mật khẩu hoặc khi migration lỗi. |
| `N3-2` / `N3-79` / `N3-81` | Pipeline CI tự động kiểm tra lint (`ruff`, `eslint`), test (`pytest`, `node --test`), quét lỗ hổng (`pip-audit`, `npm audit`) và đóng gói Docker image gắn nhãn SHA. |
| `N3-3` / `N3-82` / `N3-83` | Endpoint `/health` kiểm tra kết nối DB & trạng thái job nền; `/version` trả SHA bản phát hành. |
| `N3-4` / `N3-23` / `N3-107` | Chuỗi băm sự kiện `SHA-256` chuẩn hóa theo **RFC 8785 (JCS)**, trigger chặn sửa/xóa bản ghi `events`, phân trang lịch sử sự kiện từ máy chủ kèm kiểm tra toàn vẹn toàn chuỗi. |
| `N3-26` / `N3-131` / `N3-132` | Tác vụ nền đánh dấu bàn giao quá hạn mỗi giờ bằng hàm DB giới hạn 500 dòng/lượt (`FOR UPDATE SKIP LOCKED`), không tự ý đổi chủ sở hữu lô hàng. |
| `N3-34` / `N3-35` / `N3-133` | Phân trang danh sách lô hàng bằng con trỏ (cursor pagination 20 lô/trang), truy vấn chi tiết lô hàng trả đầy đủ danh sách tên vùng trồng gốc qua nhiều tầng tách/gộp. |
| `N3-40` / `N3-44` / `N3-47` | Tách lô có khóa dòng chống tranh chấp đồng thời (`.with_for_update(of=Lot)`), gộp lô cùng nông sản, truy vết phả hệ hai chiều đối chiếu khớp bộ đáp án [LINEAGE-ACCEPTANCE.md](LINEAGE-ACCEPTANCE.md) và hiển thị đồ thị bằng React Flow + Dagre. |

### Giai đoạn 2: Chuỗi lạnh, Thu hồi khẩn cấp, QR, PDF & Vận hành (Sprint 5 – Sprint 8)

| Nhóm nhiệm vụ Jira | Nội dung triển khai & Kiểm chứng |
|---|---|
| `N3-58` / `N3-59` / `N3-60` | Quản lý chuyến vận chuyển lạnh (`shipments`), cấp khóa cảm biến `X-Sensor-Key` (chỉ hiển thị một lần khi tạo/cấp lại, lưu băm `SHA-256`), tiếp nhận điểm đo nhiệt độ/độ ẩm bất biến và tự động mở/đóng vi phạm ngưỡng nhiệt độ liên tiếp (`temperature_violations`). |
| `N3-61` / `N3-64` / `N3-154` | Biểu đồ nhiệt độ chuyến hàng kèm dải ngưỡng an toàn `[min_temp_c, max_temp_c]`, thống kê tỷ lệ vi phạm chuỗi lạnh toàn hệ thống và job nén dữ liệu cảm biến cũ hơn 30 ngày thành bản ghi tổng hợp theo giờ (`hourly_temperature_summaries`). |
| `N3-65` / `N3-67` / `N3-149` | Sinh mã QR chuẩn SVG/PNG và hộp thoại in nhãn `30×30 mm`; trang tra cứu công khai hiển thị hành trình lô hàng, trạng thái chuỗi lạnh, cảnh báo thu hồi và bản đồ lộ trình Leaflet (`/api/v1/public/trace/{lot_code}/route`). |
| `N3-68` / `N3-69` / `N3-70` | Phát lệnh thu hồi lô hàng, tự động lan truyền xuôi dòng tới mọi lô con/cháu chưa tiêu thụ trên đồ thị phả hệ, gửi thông báo tới các tổ chức đang giữ lô bị ảnh hưởng và ghi nhận xác nhận xử lý thu hồi chỉ-thêm (`recall_confirmations`). |
| `N3-72` / `N3-155` | Xuất báo cáo truy xuất nguồn gốc chuẩn A4 định dạng **PDF** hỗ trợ tiếng Việt đầy đủ (thông tin lô, vùng trồng gốc, chuỗi băm sự kiện, lịch sử bàn giao, thông số chuỗi lạnh, thu hồi và mã QR). |
| `N3-74` | Tác vụ quét toàn vẹn chuỗi băm định kỳ (`app.jobs.integrity_scanner`), lưu lịch sử kiểm tra vào bảng `integrity_checks` và hiển thị tổng quan trên giao diện Thanh tra / Quản trị. |
| `N3-75` / `N3-141` | Ẩn danh dữ liệu định danh cá nhân (PII) của người dùng theo yêu cầu (`POST /api/v1/users/{user_id}/anonymize`), thay email bằng tombstone duy nhất và họ tên bằng `"Đã xoá theo yêu cầu"`, giữ nguyên UUID và đảm bảo chuỗi băm sự kiện vẫn hợp lệ 100%. |
| `N3-76` / `N3-160` | Sao lưu cơ sở dữ liệu hằng đêm (`pg_dump -Fc`) kèm manifest số dòng và checksum `SHA-256`, hỗ trợ đẩy lên kho lưu trữ tương thích S3 và diễn tập khôi phục tự động. |
| `N3-147` / `N3-148` / `N3-150` / `N3-151` / `N3-152` | Trung tâm thông báo nội bộ (`notifications`), hộp thư đi & gửi SMTP thu hồi (`email_outbox`), ghi nhận công đoạn chế biến (`processing_steps`), vật tư nông nghiệp đầu vào (`lot_input_materials`) và mời thành viên tổ chức qua đường dẫn token (`organization_invitations`). |

---

## 3. Các Quyết định Kỹ thuật & Giới hạn đã Ghi nhận

1. **Giới hạn bằng chứng của chuỗi băm (`N3-4`):** Chuỗi băm `SHA-256` chuẩn hóa theo `RFC 8785` kèm trigger chặn sửa/xóa giúp phát hiện ngay mọi thay đổi trái phép đối với bản ghi đã lưu, nhưng không thay thế chữ ký số phần cứng hoặc chống lại quản trị viên cơ sở dữ liệu tối cao viết lại toàn bộ chuỗi.
2. **Đáp án chuẩn phả hệ (`N3-44` / `N3-128` / `R-05`):** Sử dụng bộ đáp án cố định đã được kiểm chứng tự động trong `backend/tests/data/*-oracle.json` theo quyết định miễn trừ đếm tay hai người của chủ dự án ([LINEAGE-ACCEPTANCE.md](LINEAGE-ACCEPTANCE.md)).
3. **Lưu trữ lịch sử nghiệm thu:** Bảng đối chiếu chi tiết giai đoạn Sprint 1–4 được lưu trữ tại [docs/acceptance/sprint-1-4.csv](acceptance/sprint-1-4.csv) và các báo cáo lịch sử được bảo lưu trong [docs/acceptance/history/](acceptance/ README.md).
