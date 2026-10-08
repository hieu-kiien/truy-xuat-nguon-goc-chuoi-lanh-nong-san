# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Hệ thống phục vụ 3 nhóm đối tượng người dùng chính trong quy trình chuỗi lạnh nông sản:

1. **Nông hộ / Chủ trang trại (Grower - e.g. Nông trại Cầu Đất):**
   - *Bối cảnh:* Thao tác trực tiếp tại nông trại hoặc nhà kính công nghệ cao, quản lý thửa đất canh tác.
   - *Nhiệm vụ (Job to be done):* Khai báo và quản lý lô thu hoạch, ghi nhận nhật ký chuỗi lạnh ban đầu (nhiệt độ, độ ẩm bảo quản, GPS vị trí thu hoạch).

2. **Quản trị viên Hợp tác xã (Organization Admin - e.g. HTX Mộc Châu):**
   - *Bối cảnh:* Điều hành cấp trung tại văn phòng hợp tác xã.
   - *Nhiệm vụ (Job to be done):* Quản lý phân quyền xã viên, cấu hình danh mục vùng trồng, giám sát tổng thể các lô hàng thuộc phạm vi tổ chức.

3. **Thanh tra viên / Cơ quan quản lý chất lượng (Inspector - e.g. Chi cục Quản lý Nông lâm sản):**
   - *Bối cảnh:* Độc lập kiểm tra, đánh giá tính tuân thủ tiêu chuẩn bảo quản nông sản xuất khẩu (VietGAP, GlobalGAP).
   - *Nhiệm vụ (Job to be done):* Giám sát xuyên suốt chuỗi sự kiện lạnh, đối soát mã băm mật mã học (SHA-256) và xác minh tính bất biến của dữ liệu.

## Product Purpose

AgroChain là nền tảng quản lý quy trình chuỗi lạnh nông sản từ vùng trồng đến phân phối, giải quyết vấn đề gian lận hoặc thiếu minh bạch trong bảo quản nông sản tươi (nhiệt độ/độ ẩm bị đứt gãy trong quá trình vận chuyển nhưng bị làm giả nhật ký).

*Định nghĩa thành công:* Mọi sự kiện phát sinh trong chuỗi lạnh đều được ghi nhận tức thì, không thể bị chỉnh sửa hay xóa bỏ bởi bất kỳ bên nào (kể cả quản trị viên), đảm bảo bằng chứng xác thực tuyệt đối khi kiểm định chất lượng xuất khẩu.

## Positioning

Hệ thống tạo sự khác biệt cốt lõi thông qua **Cơ chế Nhật ký Bất biến 5 Lớp (5-Layer Immutable Ledger)** kết hợp:
- Băm SHA-256 nối chuỗi tuần tự theo chuẩn Canonical JSON RFC 8785.
- Cơ chế Trigger cấp cơ sở dữ liệu (`trg_events_prevent_update`, `trg_events_prevent_delete`) chặn đứng mọi thao tác sửa/xóa tại tầng PostgreSQL.
- Phân quyền đa tổ chức độc lập tuyệt đối nhờ cơ chế PostgreSQL `FORCE ROW LEVEL SECURITY` (RLS).

## Operating Context

- **Môi trường hoạt động:** Ứng dụng web Single Page Application (SPA), đáp ứng tốt trên máy tính để bàn (Desktop), laptop và máy tính bảng/smartphone tại hiện trường.
- **Tần suất & Nhịp điệu sử dụng:**
  - Nhập liệu theo đợt thu hoạch / vận chuyển (tạo lô, cập nhật mốc đo nhiệt độ).
  - Tra cứu, kiểm tra chéo dữ liệu thời gian thực bởi các bên liên quan.
- **Học phần & Nhóm thực hiện:** Thực tập cơ sở (TTCS) — Nhóm `TTCS_T926_K18C4_N3`.

## Capabilities and Constraints

### Chức năng đã xác thực:
- **N3-4:** Tính toàn vẹn chuỗi dữ liệu (SHA-256 + RFC 8785 canonical hash).
- **N3-5:** Quản lý xác thực an toàn (Argon2id, cookie HttpOnly `__Host-session`, Bearer fallback header, chống tấn công brute-force tự động khóa 15 phút sau 5 lần sai).
- **N3-6:** Phân quyền đa tổ chức cách ly nghiêm ngặt (PostgreSQL RLS).
- **N3-7:** Danh mục vùng trồng định danh chuẩn tọa độ GPS WGS84, mã định danh UUID v4.
- **N3-21:** Tính bất biến tuyệt đối của nhật ký sự kiện chuỗi lạnh (Append-only Trigger).
- **N3-34:** Tìm kiếm theo mã lô, sắp xếp thời gian và phân trang 20 lô/trang.

### Ràng buộc kỹ thuật:
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16.
- **Frontend:** React 19, TypeScript, Vite, Vanilla CSS hiện đại (chế độ sáng/tối đồng bộ, không dùng thư viện CSS cồng kềnh).
- **Bảo mật:** Không lưu thông tin nhạy cảm vào `localStorage`. Tuyệt đối không cho phép API cập nhật hay xóa bản ghi sự kiện (`events`).

## Brand Commitments

- **Tên nền tảng:** AgroChain (Enterprise Cold-Chain Traceability Platform).
- **Tông màu chủ đạo:** Xanh lá nông nghiệp công nghệ cao (`#15803d` / Emerald Green), phối hợp nền Slate/Zinc trung tính và các mốc cảnh báo nhiệt độ chuỗi lạnh (Xanh dương băng tuyết, Cam cảnh báo).
- **Phong cách thị giác:** Hiện đại, chuẩn Enterprise SaaS B2B, tối ưu hiển thị số liệu đo đạc (Telemetry Grid), bảng dữ liệu mật mã và dòng thời gian sự kiện (Timeline).
- **Hỗ trợ giao diện:** Đầy đủ Light Mode và Dark Mode mượt mà.

## Evidence on Hand

- **Tài khoản thử nghiệm sẵn sàng (Demo Accounts):**
  - Nông hộ: `grower@caudat.vn` (Mật khẩu: `Password123!`)
  - Quản trị HTX: `admin@mocchau.vn` (Mật khẩu: `Password123!`)
  - Thanh tra: `inspector@chicuc.gov.vn` (Mật khẩu: `Password123!`)
- **Dữ liệu mẫu thực nghiệm:** 3 tổ chức, 3 vùng trồng (Dâu tây Cầu Đất, Rau thủy canh Đà Lạt, Chè Shan Tuyết Mộc Châu).
- **Hạ tầng triển khai trực tuyến:**
  - Frontend: `https://ttcs-frontend-staging.onrender.com`
  - Backend API: `https://ttcs-backend-staging.onrender.com`

## Product Principles

1. **Minh bạch là tuyệt đối (Transparency by Cryptography):** Mọi sự kiện đo đạc hay bàn giao nông sản phải có mã băm bảo chứng, không dựa vào niềm tin mà dựa vào toán học mật mã.
2. **Ưu tiên tốc độ thao tác vận hành (Operational Efficiency):** Giao diện phải phục vụ người dùng hiện trường nhanh gọn, các nút thao tác rõ ràng, có sẵn mẫu nhanh cho demo và kiểm thử.
3. **Không đánh đổi an ninh dữ liệu (Enterprise Security First):** Cách ly triệt để dữ liệu giữa các hợp tác xã, bảo vệ phiên làm việc an toàn, phòng chống brute-force và rò rỉ token.
4. **Trực quan hóa chỉ số quan trọng (Glanceable Telemetry):** Nhiệt độ, độ ẩm, độ lệch chuẩn và vị trí GPS phải được hiển thị với tín hiệu màu sắc trực quan ngay từ cái nhìn đầu tiên.

## Accessibility & Inclusion

- Tuân thủ tiêu chuẩn tương phản màu sắc WCAG AA trên cả hai giao diện Sáng và Tối.
- Hỗ trợ đầy đủ điều hướng bằng bàn phím (`Tab`, `Enter`, `Space`) và nhãn ARIA cho người khiếm thị/sử dụng trình đọc màn hình.
- Thông báo lỗi và trạng thái hệ thống phải rõ ràng bằng tiếng Việt, tránh các thuật ngữ kỹ thuật khó hiểu đối với người nông dân.
