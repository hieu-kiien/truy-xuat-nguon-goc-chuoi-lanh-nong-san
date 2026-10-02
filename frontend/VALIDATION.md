# Kiểm chứng AgroChain redesign — 2026-10-02

Main được bảo vệ: `414eaaa2adfa901000d179f6caee9c83945f792e`. Bản thiết kế lại ở [PR #8](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/pull/8), nhánh `codex/agrochain-spatial-redesign`. Không merge/deploy, không có diff backend/services/types.

## Bằng chứng đã chạy

| Kiểm tra | Kết quả | Phạm vi |
|---|---|---|
| TypeScript/Vite + Oxlint | Qua | Production và QA entry riêng |
| Frontend unit | 8/8 | Geometry 300 điểm, timestamp/nội suy, SHA-256 đối chiếu `node:crypto` và logic canonical backend, heat/tamper độc lập, bit diff, synthetic CRUD/session, contrast tokens |
| Integrity backend hiện có | 3/3 | Canonical JSON, SHA-256, benchmark/tamper |
| PostgreSQL backend integration | 16/16 | Auth/demo allowlist, sessions, RBAC/RLS, tenant, CRUD và UUID/schema |
| Chromium synthetic UI | 71 passed, 6 skipped | 11 bài × 7 cấu hình; bài native reduced motion chuyên biệt chỉ chạy ở một cấu hình |
| Chromium + FastAPI + PostgreSQL | 12/12 | 6 bài × desktop/mobile, không retry; production entry và session thật |
| Diff / contract | Qua | `git diff --check`; API services/types/backend giữ nguyên |

Lượt xanh đầu tiên cho toàn bộ browser và backend thật: [Visual QA run 37000751980](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37000751980), commit `cfc897909e4561daaf86330811cad42b826ab79f`. CI backend/build tương ứng: [run 37000751973](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37000751973).

Lượt xác nhận cuối sau sửa scroll/capture paths: [Visual QA run 37001594645](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37001594645) và [CI run 37001594475](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37001594475), commit `3d9f9a0b346e852764d84a9c96c422f2752f3d55`. **Cả hai workflow đã completed/success; 71 UI passed + 6 skipped, 12 live passed, không flaky/retry.**

## Các hành vi browser đã kiểm tra

Desktop sáng/tối 1440×1000, tablet 1024×768, mobile sáng/tối 390×844, 320×740 và reduced motion gốc (`contextOptions.reducedMotion`). Kiểm tra overflow ngang và uncaught errors; cùng event giữa map/time/hash; pointer drag/snap và range/bàn phím; nhiệt/tamper/reset/replay; create/edit UUID không đổi dù chọn marker khác; List/Compare; ba role; 503; palette/guide focus trap, inert, Escape và focus return. Screenshot dùng Chromium, không render tĩnh hoặc hình tạo sinh.

Live suite dùng database PostgreSQL 16 dùng một lần. Login credential của tài khoản thường được tạo ngẫu nhiên trong CI; password không đưa vào FE/source/log/artifact. Demo đăng nhập qua allowlist thật. Grower/Admin GET 200 và records đúng tổ chức; Inspector 403 tại RBAC. Create 201/edit/reload giữ UUID và persistence; tenant khác không thấy record trong list và GET ID bị 403. Logout rồi reload, GET không xác thực trả 401.

Các test RLS trong backend CI mới là bằng chứng database isolation; ảnh mô hình Security X-Ray không thay thế chúng. QA mock chỉ kiểm tra UI response, không chứng minh backend security.

## Screenshot

Các ảnh chính Gateway, Trace, Atlas, Journey, Forensics, Security và Field Guide được lưu trong artifact `agrochain-live-browser-qa` (production entry, API thật) và `agrochain-visual-qa` (7 cấu hình synthetic). Artifact CI giữ 14 ngày. Bộ PNG bàn giao và nguồn chụp sẽ được ghi tại `screenshots/README.md`.

## Hiệu năng và giới hạn

Production bundle cuối: JS **337.48 kB / gzip 102.55 kB**, CSS **107.64 kB / gzip 20.45 kB**. Không thêm runtime dependency; Playwright chỉ dev. Production entry không import mock/QA. RAF/timer/listener/observer có cleanup, animation hữu hạn và reduced-motion fallback.

Đã xem ảnh thật desktop/mobile ở hai theme và sửa lỗi nhãn marker tràn. Chưa kiểm chứng screen reader thủ công, browser zoom 200%, Safari/Firefox, thiết bị yếu hoặc đo FPS/CLS; không tuyên bố 60fps hay WCAG toàn ứng dụng đã được chứng nhận. Token contrast được tính bằng test, không thay thế kiểm tra từng pixel.

Trace/Cold Chain là fixture local, không sensor live. Hash tính thật; tamper sửa đúng event 03 và event 04 mất ancestry. Ngoại lệ nhiệt có thể vẫn hợp lệ về mật mã. Security lấy HTTP/records thật; lớp nội bộ là mô hình suy từ code vì API không xuất per-layer spans.
