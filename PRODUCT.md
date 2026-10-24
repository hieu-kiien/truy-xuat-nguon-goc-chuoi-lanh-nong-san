# Định hướng Sản phẩm — VietFarm Trace (AgroChain)

Ứng dụng web quản lý và truy xuất nguồn gốc chuỗi lạnh nông sản từ vùng trồng đến phân phối và người tiêu dùng. Dự án học phần Thực tập Cơ sở (TTCS) của nhóm **TTCS_T926_K18C4_N3**; dữ liệu trình diễn là dữ liệu giả lập phục vụ kiểm thử và bảo vệ đồ án.

## 1. Nhóm người sử dụng

- **Nông hộ (`grower`):** Quản lý vùng trồng, khai báo lô thu hoạch, ghi nhận vật tư đầu vào, công đoạn sơ chế, nhật ký sự kiện canh tác và khởi tạo bàn giao.
- **HTX / Quản trị đơn vị (`org_admin`):** Quản lý lô hàng của đơn vị, tách/gộp lô, bàn giao, quản lý thành viên & lời mời tham gia tổ chức, xử lý thu hồi trong phạm vi đơn vị.
- **Đơn vị vận chuyển (`transporter`):** Quản lý chuyến vận chuyển lạnh (`shipments`), cấp khóa thiết bị cảm biến (`X-Sensor-Key`), theo dõi biểu đồ nhiệt độ/độ ẩm và cảnh báo vi phạm ngưỡng nhiệt độ.
- **Đơn vị phân phối (`distributor`):** Tiếp nhận bàn giao, quản lý vị trí kho/điểm bán, tách/gộp lô thương mại, ghi nhận tiêu thụ và xác nhận xử lý thu hồi.
- **Thanh tra (`inspector`):** Tra cứu nguồn gốc xuyên tổ chức, kiểm tra phả hệ hai chiều, xác minh tính toàn vẹn chuỗi băm sự kiện (`SHA-256`), phát lệnh thu hồi khẩn cấp, xuất báo cáo PDF A4 và tra cứu nhật ký kiểm toán (`audit_logs`).
- **Quản trị hệ thống (`system_admin`):** Quản lý tổ chức, người dùng, danh mục nông sản, giám sát tổng thể chuỗi lạnh, quét toàn vẹn định kỳ và thực hiện ẩn danh dữ liệu định danh cá nhân (PII) theo yêu cầu.
- **Người tiêu dùng (Công khai):** Quét mã QR `30×30 mm` hoặc nhập mã lô để xem hành trình nông sản, bản đồ di chuyển, trạng thái kiểm định chuỗi lạnh, trạng thái thu hồi và tải báo cáo PDF mà không cần đăng nhập.

## 2. Phạm vi sản phẩm đã hoàn thiện (Sprint 1 – Sprint 8)

Toàn bộ các phân hệ từ Sprint 1 đến Sprint 8 (`N3-1` → `N3-160`) đã được triển khai và kiểm chứng:

1. **Xác thực, RBAC & Cô lập dữ liệu đa tổ chức (PostgreSQL RLS):** Đăng nhập JWT, phân quyền theo vai trò, quản lý thành viên, mời thành viên bằng đường dẫn token và ẩn danh PII không ảnh hưởng chuỗi băm.
2. **Danh mục nông sản, Vùng trồng & Lô thu hoạch:** Khai báo nông sản kèm ngưỡng nhiệt độ lạnh, vùng trồng kèm tọa độ GPS, lô thu hoạch, vật tư sử dụng, công đoạn chế biến và nhập dữ liệu hàng loạt qua CSV.
3. **Phả hệ lô hàng (DAG Lineage), Bàn giao & Phân phối:** Tách lô an toàn đồng thời, gộp lô cùng nông sản, đồ thị phả hệ trực quan bằng React Flow/Dagre, bàn giao liên tổ chức có kiểm soát quá hạn tự động, quản lý vị trí phân phối và tiêu thụ.
4. **Giám sát Chuỗi lạnh & Cảm biến tự động:** Quản lý chuyến vận chuyển lạnh, tiếp nhận dữ liệu nhiệt độ/độ ẩm từ thiết bị qua `X-Sensor-Key`, tự động phát hiện vi phạm ngưỡng nhiệt độ liên tiếp, biểu đồ nhiệt độ theo thời gian thực và nén dữ liệu cảm biến theo giờ.
5. **Thu hồi khẩn cấp & Trung tâm thông báo:** Thu hồi tự động lan truyền xuôi dòng theo đồ thị phả hệ đến mọi lô con/cháu chưa tiêu thụ, gửi thông báo nội bộ & email thu hồi, theo dõi xác nhận thu hồi bất biến của từng đơn vị.
6. **Nhãn QR chuẩn in ấn & Báo cáo PDF A4:** Sinh mã QR kèm nhãn in `30×30 mm`, trang tra cứu công khai tích hợp bản đồ hành trình và xuất báo cáo truy xuất nguồn gốc PDF chuẩn A4 tiếng Việt.

Chi tiết tiêu chí nghiệm thu xem tại [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md).

## 3. Nguyên tắc thiết kế giao diện (VietFarm Trace v3)

- **Trực quan, ưu tiên nghiệp vụ:** Hiển thị tên nông sản, vùng trồng và đơn vị dễ hiểu; mã kỹ thuật và mã băm hiển thị gọn kèm nút sao chép nhanh.
- **Thao tác mượt mà, không chuyển trang thừa:** Chỉnh sửa và thực hiện nghiệp vụ qua hộp thoại (modal) và ngăn kéo chi tiết; toàn bộ nhãn nút, thông báo lỗi và kết quả hiển thị bằng tiếng Việt rõ ràng.
- **Phân trang & Đồ thị phả hệ rõ ràng:** Danh sách lô hàng, sự kiện và nhật ký kiểm toán được phân trang từ phía máy chủ; đồ thị phả hệ sử dụng bố cục tự động bằng React Flow và Dagre.
- **Hỗ trợ giao diện Sáng / Tối (Light / Dark Mode) và điều hướng bàn phím:** Tương thích màn hình máy tính và thiết bị di động, hỗ trợ phím tắt tra cứu nhanh (`Ctrl+K`).

## 4. Bảo đảm toàn vẹn dữ liệu và Giới hạn kiến trúc

- Tầng API kiểm tra quyền RBAC kết hợp tầng cơ sở dữ liệu PostgreSQL kiểm tra **Row-Level Security (RLS)** theo phiên làm việc; các trigger cơ sở dữ liệu chặn sửa/xóa bản ghi đối với tài khoản runtime trên các bảng bất biến (`events`, `temperature_readings`, `recall_confirmations`, `audit_logs`).
- Chuỗi băm `SHA-256` chuẩn hóa theo **RFC 8785** giúp phát hiện ngay lập tức mọi hành vi sửa đổi nội dung sự kiện hoặc làm đứt gãy thứ tự chuỗi khi đối chiếu. Như đã ghi nhận rõ trong hồ sơ kiến trúc, cơ chế này không thay thế chữ ký số phần cứng hoặc chống lại quản trị viên cơ sở dữ liệu tối cao viết lại toàn bộ chuỗi.

Chi tiết kỹ thuật xem tại [docs/N3-4-INTEGRITY.md](docs/N3-4-INTEGRITY.md), [docs/database.md](docs/database.md) và hướng dẫn chạy tại [README.md](README.md).
