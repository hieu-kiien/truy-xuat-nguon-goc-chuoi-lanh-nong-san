# Gateway tương tác — 02/10/2026

> Báo cáo này ghi bước triển khai Gateway trước cập nhật workspace. Kết quả tổng thể mới nhất ở [VALIDATION.md](VALIDATION.md); package Playwright chỉ là dev dependency mới, không dependency runtime.

Đã đưa vào nhánh `codex/agrochain-spatial-redesign` và PR #8. Chưa merge/deploy. Đây là bản mở rộng của frontend local đang được thiết kế lại, không phải một bản thay đổi backend.

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

## Kiểm chứng browser bổ sung

GitHub Actions đã chạy Gateway cùng toàn bộ workspace trên 7 cấu hình: desktop light/dark, tablet, mobile light/dark, 320px và native reduced motion. Các bài Gateway kiểm tra drag/snap, range/bàn phím, heat/tamper độc lập, focus lỗi, auth tổng hợp và logout. Bộ live dùng production entry, FastAPI + PostgreSQL thật để kiểm tra login credential, demo ba vai trò, session reload/logout, allowed/403 và farms persistence/isolation.

Ảnh Gateway desktop/mobile được chụp bằng Chromium thật. Build size và kết quả tổng thể mới nhất ở [VALIDATION.md](VALIDATION.md). Screen reader thủ công, 200% zoom, FPS/CLS trên thiết bị thật chưa được xác nhận.
