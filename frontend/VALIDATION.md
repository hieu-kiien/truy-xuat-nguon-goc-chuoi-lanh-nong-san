# Kiểm chứng AgroChain redesign — 2026-10-02

## Đã chạy

- TypeScript/Vite production build: JS 337.43 kB / gzip 102.51 kB; CSS 107.58 kB / gzip 20.43 kB. TypeScript/Vite preview build cũng qua.
- Oxlint (bao gồm source và QA).
- 8 frontend domain/transport/token tests: hình học 300 điểm; timestamp/nội suy; bốn tổ hợp heat/tamper; digest thực bằng `node:crypto`; canonical payload và kết quả chain được đối chiếu bằng logic `backend/benchmark/integrity_benchmark.js`; bit diff; mock sessions/tenant/CRUD; token contrast.
- 3 kiểm thử integrity sẵn có trong backend: canonical JSON, SHA-256 và benchmark 1000 event/tamper.
- Browser test discovery: 77 trường hợp từ 11 bài × 7 cấu hình. Đây là discovery, chưa phải 77 test pass.
- `git diff --check`; không có thay đổi backend/services/types.

## Chưa đạt kiểm chứng đầy đủ

Browser local: `npx playwright install chromium` thất bại vì archive tải xuống không giải nén được. Khi chạy một bài Playwright, runner dừng tại launch do thiếu executable; chưa vào ứng dụng. CUA browser từ chối `http://127.0.0.1:5173` với `ERR_BLOCKED_BY_CLIENT`.

Vì vậy chưa có screenshot thực, chưa thể kết luận desktop/tablet/mobile, light/dark rendering, touch/focus, native reduced motion, screen reader, zoom hoặc FPS/CLS đã đạt. Không dùng static render hay build để thay kết quả browser.

Backend/database thật chưa chạy trong workspace. Chưa kiểm thử end-to-end login/demo login, session, roles, persistence và PostgreSQL RLS. QA mock chứng minh UI xử lý các response tổng hợp, không chứng minh bảo mật backend.

## Tự động hóa đã chuẩn bị

`qa/preview.tsx` chạy component thật với transport synthetic độc lập. Production entry không import mock; fixture/cấu hình demo QA không đi vào production bundle. `npm run test:browser` kiểm tra và chụp Gateway, Trace, Atlas, Journey, Forensics, Security, Guide và các trạng thái tamper/compare/create/ba role trên 7 cấu hình.

Workflow `Frontend Visual QA` chạy trên PR vào main hoặc manual dispatch, lưu ảnh/trace/HTML report trong artifact `agrochain-visual-qa`. CI backend/RLS hiện có được giữ nguyên. Chưa có workflow result được tuyên bố trong tài liệu này; cần cập nhật sau khi chạy thực.

## Phạm vi dữ liệu

Trace và Cold Chain là fixture local, không giả sensor live. Hash được tính thật lúc chạy; tamper thay đúng `temp_c` event 03, event 04 mất ancestry. Nhiệt 9.9°C trước seal vẫn có integrity hợp lệ. Security theo HTTP thực và records response; các tầng RBAC/tenant/RLS mô tả kiến trúc đã đọc, không phải span đo trực tiếp.
