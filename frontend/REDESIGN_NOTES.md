# AgroChain — kiến trúc và bàn giao frontend

Bản thiết kế lại trên main hardened `414eaaa2adfa901000d179f6caee9c83945f792e`, xác nhận lại main GitHub ngày 2026-10-02. React + TypeScript + Vite + custom CSS, không thay backend hoặc API.

## Trước / sau

Trước: shell/sidebar, CSS tập trung, các panel farms/security/integrity và hash minh họa cố định.

Sau: Gateway tương tác; dock dẫn tới 6 trải nghiệm riêng; map/time/evidence dùng ngữ cảnh sự kiện chung. `App` vẫn khởi tạo health/session, đăng nhập và logout. `FarmWorkspace` sở hữu farms API, cursor/scenario local và request probe. `FarmAtlas` quản lý các dạng đọc và form; ID đang sửa độc lập với marker đang chọn. Domain functions độc lập DOM tính thời gian, hình học và digest. CSS theo lớp/miền trải nghiệm.

Đã gỡ các component và CSS cũ không còn import, gồm `IntegrityPanel` chứa hash tĩnh. Chưa có endpoint shipment/sensor; không tạo dữ liệu backend giả để làm animation.

## Ranh giới được giữ

`src/services/api.ts`, `src/types/index.ts` và toàn bộ backend không có diff. Login/demo/current-user/logout/health/farms vẫn dùng payload/endpoint, cookie credentials và session header cũ. Demo vẫn cần cờ frontend và cấu hình/allowlist backend; không có mật khẩu demo trong FE. `hasPermission` giữ nguyên. Tenant filtering và RLS do backend/database quyết định; việc ẩn nút không được xem là bảo mật.

Farm list/create/edit hoàn chỉnh qua service hiện có, giữ UUID khi sửa, không thêm delete endpoint. Mẫu GPS có sẵn là lựa chọn người dùng trong form; không tự ghi dữ liệu. Tamper/nhiệt và guide chỉ sửa trạng thái local; Security chỉ GET.

## Inventory tương tác đã triển khai

| Hiệu ứng | Ý nghĩa / trigger | Kỹ thuật và chi phí | Fallback tiếp cận |
|---|---|---|---|
| Kiện hàng kéo/snap | Người dùng khám phá một tuyến local | Pointer capture, chiếu lên 241 điểm, RAF; thấp | Click chặng, arrows/Home/End, range |
| Route progress | Thời gian tương ứng vị trí/telemetry | SVG prefix de Casteljau; thấp | Nhãn thời điểm/GPS/giá trị |
| Camera theo mốc | Chọn góc nhìn gần một sự kiện | Transform 480ms; thấp | Nút toàn tuyến, marker focus; reduced motion tức thời |
| Shared lens | Cùng event đi qua map/time/hash | Native View Transitions, snapshot hữu hạn; trung bình | Feature detection, cập nhật tức thời |
| Timeline scrubber | Thời gian liên tục giữa mẫu ghi | Native range, nội suy; thấp | `aria-valuetext`, bước trước/sau |
| Thermal ribbon | Thể hiện đoạn fixture ngoại lệ nhiệt | SVG amber, chỉ bật theo scenario; thấp | Caption và trạng thái nhiệt riêng |
| GPS inspector | Chọn vị trí farms thật của tenant | Camera, crosshair, lock hữu hạn; thấp | Marker button, List, tọa độ đầy đủ |
| Area glyph | Tỷ trọng diện tích, không ranh thửa | Circle theo căn tỷ trọng; thấp | Giá trị ha / chú thích |
| Inspector create/edit | Mở form theo record UUID cố định | React form/service, panel state; thấp | Label/constraint, Escape/cancel/focus return |
| Hash replay | Kiểm chứng canonical bằng SHA-256 lại | Web Crypto, 4 timer hữu hạn; thấp | Bước thủ công và trạng thái chữ |
| Digest diff | So sánh seal ghi với digest tính lại | 64 hex + bit XOR thực; thấp | Chuỗi đầy đủ, số khác biệt, underline |
| Fracture/ancestry | Sửa một source field sau seal | Băm thật, gãy link 03→04, một propagation; thấp | JSON trước/sau; mismatch khác ancestry |
| Request X-Ray | Gửi GET và nhận HTTP/records thực | Promise lifecycle, không thêm delay; thấp | 401/403/200/error chữ, list lớp theo thứ tự |
| Tenant membranes | Records nào API đã trả về | Dữ liệu response, miền còn lại trừu tượng; thấp | UUID/org ID, cảnh báo nếu org không khớp |
| Command palette | Đi tới phân hệ/thao tác | Lọc 8 lệnh, modal; thấp | Ctrl/Cmd+K, arrows/Enter/Escape, focus trap |
| Spotlight guide | Giải thích tùy chọn theo chương | Mask tĩnh, observer/RAF có cleanup; thấp | Dialog caption, exit/Escape, inert/focus return |
| Theme | Đọc trong sáng/tối | Semantic tokens, preference cũ; thấp | Accessible name, không radial effect dư thừa |

Không dùng hiệu ứng scramble hash, số telemetry loop giả, magnetic controls, 3D hoặc scroll physics không có giá trị miền dữ liệu. Các ý tưởng không dùng được ghi trong nghiên cứu.

## Tiếp cận

Semantic HTML, main/heading/nav, native form/range/details và table. Tương tác có click/keyboard tương đương; không bắt buộc hover. Modal trap Tab, Escape, inert và trả focus về trigger nếu còn tồn tại, nếu không về heading hiện tại. Điều hướng phân hệ đưa cuộn về đầu và focus heading; không chiếm lại focus khi đóng overlay. Mobile có menu phiên và logout.

Hash và lỗi nhiệt độc lập; màu có text/shape. Dữ liệu nội suy ghi rõ, evidence tham chiếu event ghi gần nhất. SVG chart có phần HTML tương đương. Đã kiểm tra tương phản các token chữ/trạng thái/focus bằng công thức WCAG; browser automation đã kiểm tra focus/keyboard, hai theme, reduced motion và 5 kích thước viewport. Screen reader thủ công, tương phản từng pixel và 200% zoom còn cần đánh giá trực tiếp.

## Hiệu năng

Không dependency runtime mới; Playwright chỉ dev để kiểm thử. SVG nhỏ, 4 fixture, không animate bảng lớn; position dùng transform, chỉ đo hình học lúc cần. View Transition giữ snapshot hai view trong thời gian ngắn, không loop. Replay/timer/RAF/listener/observer được cleanup. Không đo FPS/CLS bằng browser nên không tuyên bố 60fps đã đạt.

Build, kết quả test, screenshot và giới hạn nằm tại [VALIDATION.md](VALIDATION.md). Cách chạy local/CI: [qa/README.md](qa/README.md).
