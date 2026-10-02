# Gateway tương tác — 02/10/2026

> Báo cáo này ghi bước triển khai Gateway trước cập nhật workspace. Kết quả tổng thể mới nhất ở [VALIDATION.md](VALIDATION.md); package Playwright chỉ là dev dependency mới, không dependency runtime.

Đã triển khai trong working tree `codex/agrochain-redesign`. Chưa push/merge/deploy. Đây là bản mở rộng của frontend local đang được thiết kế lại, không phải một bản thay đổi backend.

## Trải nghiệm đã có

- Bố cục editorial: tiêu đề tiếng Việt và canvas địa hình ở bên trái; form đăng nhập và passport demo ở bên phải. Tablet/mobile chuyển thành một cột và có link đi thẳng tới form.
- Bốn chặng của fixture hiện có: vùng trồng/thu hoạch, làm lạnh, xe lạnh, kho. Sơ đồ không tự nhận là tuyến đường khảo sát/GPS live.
- Kéo kiện hàng theo đường cong; vị trí và phần tuyến đã đi khớp nhau bằng phép chia Bézier. Thả tay bắt vào chặng gần nhất. Nhấn kiện hàng để tới chặng tiếp; mũi tên/Home/End, nút chặng và native range cung cấp đường thao tác tương đương.
- Nhiệt độ và thời gian nội suy khi kéo; có nhãn nội suy, không trình bày các giá trị đó như mẫu đo thật. Tại chặng, dùng các giá trị fixture tương ứng.
- Hai thử nghiệm độc lập: tăng nhiệt độ xe lạnh tới 9.9°C trước khi niêm phong; sửa `temp_c` thành 99.9 sau khi niêm phong. Cả hai đều chỉ sửa trạng thái local. Khôi phục riêng hoặc đặt lại toàn bộ.
- Web Crypto tính SHA-256 thực bằng logic fixture dùng chung. Nhiệt độ vượt ngưỡng vẫn có hash hợp lệ; tamper gây mismatch ở sự kiện 03 và ancestry invalid ở sự kiện 04. Trong lúc tính hoặc khi Web Crypto lỗi, không kết luận hợp lệ.
- Các seal có text/accessible label, connector đứt tại đúng liên kết và phản hồi downstream chạy hữu hạn. Disclosure cho xem giá trị trước/sau, hash ghi và hash tính lại đầy đủ; không hash scramble giả.
- Passport có nút chọn/điền email tách khỏi nút đăng nhập demo. Tên passport đang xem xuất hiện trong canvas; đổi passport không thay tenant thật hoặc gọi API.
- Form tiếp tục dùng `login` / `demoLogin`, allowlist và cấu hình demo cũ. Password khởi tạo rỗng; không thêm mật khẩu demo. Native `reportValidity()` đưa ra lỗi trường bắt buộc/email, lỗi API vẫn có alert và focus.

## Kiến trúc

- `src/components/GatewayJourney.tsx`: tương tác và bằng chứng local, không import/call service API.
- `src/domain/gatewayJourney.ts`: hình học tuyến và nội suy nhiệt độ, độc lập DOM.
- `src/domain/demoScenario.ts`: logic hash-chain hiện có được tái sử dụng, không đổi.
- `src/components/LoginView.tsx`: ghép playground và giữ auth handlers.
- `src/styles/gateway.css`: bố cục/form/passport; `gateway-journey.css`: canvas, telemetry và motion. Gỡ responsive Gateway cũ để tránh cascade xung đột; giữ responsive các workspace khác.

Không có package runtime mới. Services, types, backend, CSP và permission policy không thay đổi trong bước này.

## Tiếp cận và hiệu năng

- Nút quan trọng tối thiểu 44px; inputs 16px; mô tả/status khoảng 11–14px. Các annotation cartographic nhỏ chỉ trang trí, trạng thái quan trọng có bản HTML dễ đọc.
- `prefers-reduced-motion` tắt các animation hữu hạn; vẫn giữ điều khiển kéo trực tiếp vì đó là input do người dùng chủ động. Không có loop giả live.
- Không modal mới. Link tới form có đích focusable; các nút chặng và range có nhãn. Hash disclosure dùng `details/summary` native.
- Lấy kích thước SVG một lần khi bắt đầu kéo. Chiếu pointer lên 241 sample đường cong; cập nhật tối đa một RAF đang chờ. Kiện hàng di chuyển qua transform; RAF bị hủy khi kết thúc/cancel/unmount. Kết quả hash cũ bị bỏ qua sau cleanup effect.
- Mở disclosure có thể làm nội dung cao hơn theo hành động người dùng. Không claim đã đo CLS/frame rate trên browser.

## Đã kiểm tra

- `npm run build`: qua TypeScript + Vite. Bundle sau cập nhật: JS 323.77 kB / gzip 98.64 kB; CSS 87.69 kB / gzip 17.11 kB. Đây là toàn frontend redesign, không phải riêng Gateway.
- `npm run lint`: qua.
- `node --test tests/gateway-journey.test.mjs` từ thư mục frontend (Node 24 theo `.nvmrc`): 3 test qua. Kiểm tra projection/prefix cho 300 điểm, clamp/boundary; interpolation; bốn tổ hợp heat/tamper, digest đối chiếu độc lập bằng `node:crypto`, invalid ancestry và reset/không mutate fixture.
- Static render bằng Vite SSR + React server renderer: qua với demo bật và tắt; xác nhận form/autocomplete, range/labels, bốn nút chặng, disclosure tính toán chưa xong không claim verified, trạng thái demo theo cấu hình và ID không trùng. Static render không thay browser interaction test.
- `git diff --check`: qua. Không có diff trong `src/services`, `src/types` hoặc backend.

## Chưa kiểm chứng trong browser

Môi trường hiện tại thiếu browser executable; CUA đã từ chối local preview ở lần kiểm tra trước. Vì vậy chưa có screenshot desktop/mobile, kiểm tra focus/touch thực, screen reader, dark/light rendering, reduced-motion rendering hay đo FPS. Chưa có backend/database test khả dụng để chạy login thật/demo theo role end-to-end. Các mục đó vẫn mở, không dùng build/SSR để tuyên bố đã qua.

Khi có preview/browser: thử 1440×1000, 1024×768, 768×1024, 390×844 và 320×740 ở light/dark; Tab toàn màn hình; drag/cancel/snap/click sau drag; range arrows/Home/End; heat và tamper riêng/kết hợp/reset; Web Crypto failure; login invalid/pending/error/success, demo bật/tắt. Kiểm tra không che form và không overflow ngang ở 200% zoom.
