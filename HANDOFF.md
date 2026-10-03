# Bàn giao AgroChain — 2026-10-03 (Asia/Saigon)

Tài liệu này ghi trạng thái khi chuyển phát triển từ ChatGPT sang máy cá nhân. Bản thiết kế mới đã merge vào `main`. Commit mã nguồn trước lần bàn giao tài liệu này: `83a1ac227df0be772b7c322fd803c7a2b0d8616e`.

## Đã đồng bộ

- [PR #8](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/pull/8): toàn bộ frontend React + TypeScript + Vite + custom CSS được thiết kế lại; squash commit `0ecc365431156ee3207da1c6af6f992e8c858c38`.
- [PR #9](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/pull/9): sửa vòng chờ Render/CI; commit `83a1ac2`.
- Gateway tương tác; Trace Command Center; Farm Atlas Map/List/Compare và create/edit; Cold Chain Journey; Integrity Forensics; Security X-Ray; command palette, theme và guide tùy chọn.
- Backend, API services/types, session, RBAC/RLS và tenant isolation không bị viết lại. Không thêm mật khẩu demo vào frontend.
- Workspace nguồn sạch trước khi viết ghi chú này. Tree bản frontend đã bàn giao trùng tree PR #8 sau merge; phần thêm của PR #9 chỉ là workflow deploy.

## Chạy ở máy cá nhân

Cần Git và Docker Desktop đang bật. Để giữ nguyên các thay đổi trong checkout cũ, có thể clone vào thư mục mới:

```bash
git clone https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san.git agrochain-local
cd agrochain-local
docker compose up --build -d
```

Sau khi backend hoàn tất bootstrap/migration/seed:
- Giao diện: http://localhost:5173
- Swagger: http://localhost:8000/docs
- Compose bật demo login ở frontend và backend phát triển; dùng các nút demo cho Grower, Organization Admin và Inspector. Không cần password demo.

Xem trạng thái/log và dừng:
```bash
docker compose ps
docker compose logs --tail=100 backend frontend
docker compose down
```

Compose giữ dữ liệu trong volume. Không dùng `down -v` khi muốn giữ dữ liệu local.

Nếu sửa FE và muốn Vite cập nhật ngay, dùng Node 24, chạy backend/database bằng Docker:
```bash
docker compose up --build -d database backend
cd frontend
npm ci
```

Tạo `frontend/.env.local` từ `.env.example`, đặt:
```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_ENABLE_DEMO_LOGIN=true
```

Rồi chạy `npm run dev`. Nếu container frontend cũ chiếm cổng 5173, dừng bằng `docker compose stop frontend` từ thư mục gốc trước khi chạy Vite. Các file env local không commit. Không bật backend demo trong production.

## Kiểm thử đã thực hiện

- TypeScript/Vite build, Oxlint, 8 frontend unit và 3 backend integrity tests qua.
- 16 integration tests backend/PostgreSQL qua.
- Chromium UI: 71 passed, 6 skipped có chủ đích cho test reduced motion chuyên biệt, không flaky/retry.
- Chromium + FastAPI + PostgreSQL thật: 12 passed trên desktop/mobile. Bao gồm login credential ngẫu nhiên, demo 3 role, session/logout/401, Grower/Admin GET 200, Inspector 403, tenant isolation và create/edit giữ UUID.
- Viewport: desktop light/dark, tablet, mobile light/dark, 320px và native reduced motion.
- Lượt xác nhận cuối trước merge: [Visual QA 37003611730](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37003611730), [CI 37003611775](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37003611775), trên head `9a1ee7ebb941c691fffbb3c2fd375071ad8b8538`.
- CI trên main `83a1ac2`: [37006036926](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37006036926), success. Commit tài liệu bàn giao sau đó có CI riêng; không coi kết quả trên là kết quả của commit mới.
- Chi tiết/giới hạn: [frontend/VALIDATION.md](frontend/VALIDATION.md). Test local: [frontend/qa/README.md](frontend/qa/README.md).

## Chưa hoàn tất: triển khai domain

Frontend staging: https://ttcs-frontend-staging.onrender.com/
Backend staging: https://ttcs-backend-staging.onrender.com/

Kiểm tra trực tiếp ngày 2026-10-03: frontend HTTP 200 nhưng vẫn phục vụ asset cũ `/assets/index-BtAhDigI.js`, không có meta `agrochain-build`. Domain chưa được xác nhận chạy redesign.

- Workflow kích hoạt triển khai xanh không chứng minh domain đã cập nhật. Log trước đó báo không có `RENDER_DEPLOY_HOOK`, dựa vào Render GitHub auto-deploy.
- Đã sửa vòng chờ: Render “After CI Checks Pass” không còn bị workflow chặn trong lúc workflow đợi domain. `scripts/verify_staging.py` kiểm tra riêng phiên bản frontend/API.
- [Lượt kiểm tra rollout độc lập 37006277742](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37006277742) thất bại sau 5 phút: domain vẫn bản cũ. Browser smoke trong workflow này chưa chạy, không được tính là đã pass.
- Nhánh `codex/staging-observe-83a1ac2` chỉ là quan sát triển khai, không merge, không cần dùng để phát triển. Dùng `main`.
- OpenAPI backend quan sát ngày 2026-10-02 không có demo-login và có lots, khác repository hiện tại. Lần GET OpenAPI 2026-10-03 timeout; chưa có bằng chứng đồng bộ backend. Cần đối chiếu đúng service/repo/branch/build và database/migrations trước khi thay triển khai backend.
- Kết nối Render đã khả dụng ngày 2026-10-03, nhưng chưa có workspace được xác nhận/chọn; chưa đọc service/log hoặc kích hoạt deploy qua kết nối này. Workspace được liệt kê có tên “My Workspace”. Không suy đoán nguyên nhân cụ thể khi chưa đọc cấu hình/log.
- Việc người dùng chuyển sang local chưa giải quyết triển khai. Chưa nghiệm thu login/demo/CRUD trên domain mới.

Frontend build có meta `agrochain-build` lấy public commit SHA từ `RENDER_GIT_COMMIT` hoặc `GITHUB_SHA`; build local hiện `local`. Nó không phải secret.

## Ranh giới và việc nên tiếp tục

Trace/telemetry là fixture local đã ghi rõ, không phải cảm biến live. SHA-256 tính thật theo canonical payload; ngoại lệ nhiệt độc lập với hash tampering. Security gọi GET thật, nhưng các lớp nội bộ là mô hình giải thích, API chưa xuất spans từng lớp.

Chưa kiểm tra thủ công screen reader, zoom 200%, Safari/Firefox hoặc máy yếu; chưa đo FPS/CLS. Không tuyên bố ứng dụng hoàn hảo/đạt 60fps/WCAG chứng nhận.

Sau khi chạy local: kiểm tra 3 role, create/edit farm, heat/tamper độc lập, keyboard/reduced motion và mobile. Tiếp tục phát triển trên nhánh mới từ main; giải quyết domain riêng sau khi có quyền truy cập đúng service.

## Tài liệu và ảnh trong repo

- [DESIGN_RESEARCH.md](frontend/DESIGN_RESEARCH.md)
- [DESIGN_SYSTEM.md](frontend/DESIGN_SYSTEM.md)
- [REDESIGN_NOTES.md](frontend/REDESIGN_NOTES.md): kiến trúc trước/sau, interaction inventory, accessibility/performance.
- [screenshots/README.md](frontend/screenshots/README.md): nguồn và phạm vi 14 PNG desktop/mobile đã commit, chụp bằng browser; không phải ảnh domain đã triển khai mới.
