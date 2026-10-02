# Kiểm thử giao diện AgroChain

`preview.html` là entry độc lập dùng chính các React component production, nhưng có transport giả lập rõ ràng. Nó không kết nối backend, không gửi mật khẩu, và chỉ giữ thao tác CRUD trong bộ nhớ. Không dùng bản này để khẳng định authentication, RBAC hoặc PostgreSQL RLS thật đã đạt kiểm thử. Vite production vẫn chỉ build `index.html`; không có mock backend trong bundle production.

## Xem nhanh không cần backend

```sh
cd frontend
npm ci
npm run preview:visual
```

Mở địa chỉ mà Vite in ra, thêm `/preview.html`. Banner cho phép mở Gateway, ba vai trò, hai theme và lỗi 503 tổng hợp. Các thay đổi mất khi tải lại. Ô mật khẩu chỉ nhận một giá trị thử bất kỳ; không nhập mật khẩu thật. Nút demo dùng API giả lập của preview, không đổi cấu hình production.

## Kiểm thử và chụp màn hình

```sh
cd frontend
npm ci
npx playwright install --with-deps chromium
npm test
npm run lint
npm run build
npm run build:preview
npm run test:browser
```

Bộ Playwright kiểm tra 7 môi trường: desktop sáng/tối 1440×1000, tablet 1024×768, mobile sáng/tối 390×844, mobile 320×740 và reduced motion gốc của trình duyệt. 11 bài kiểm tra được mở rộng thành 77 trường hợp; bài reduced-motion chuyên biệt chỉ chạy ở project tương ứng.

Các bài kiểm tra chụp toàn bộ Gateway, Trace, Atlas, Cold Chain, Forensics, Security, Field Guide và trạng thái tamper/compare/create/ba vai trò vào `test-results/`. HTML report nằm trong `playwright-report/`; chạy `npx playwright show-report` để xem. Đây là ảnh chụp phục vụ đánh giá, chưa có baseline đã duyệt để khẳng định pixel-regression.

Workflow `Frontend Visual QA` chạy bộ kiểm thử và tải report/ảnh dưới artifact `agrochain-visual-qa` trên GitHub Actions khi có PR vào main hoặc khi chạy thủ công. Workflow chưa được chạy từ workspace này và chưa có ảnh để bàn giao.

## Kiểm thử backend thật

Chạy ứng dụng qua `npm run dev` và cấu hình `VITE_API_BASE_URL` theo `.env.example`. Bật demo chỉ trong môi trường backend đã cho phép demo với allowlist; không thêm mật khẩu demo vào FE.

Kiểm tra login bằng tài khoản thực được cấp, demo login, reload phiên và logout. Grower/Organization Admin: list/create/edit với UUID giữ nguyên. Inspector: kiểm tra farm GET bị 403 trong Security X-Ray. Kiểm tra tenant A/B bằng các danh tính khác nhau. Xác minh RLS bằng các test PostgreSQL hiện có trong `backend/tests/test_n36_security.py` và `test_n37_farms.py`, không bằng ảnh của sơ đồ.

## Trạng thái tại 2026-10-02

Unit tests và build/lint đã chạy trong workspace. Browser suite mới được kiểm tra khả năng discovery; chạy thực bị chặn vì chưa cài được Chromium. Browser đám mây cũng từ chối local origin bằng `ERR_BLOCKED_BY_CLIENT`. Không có screenshot hay kết quả bàn phím/contrast/viewport thực được tuyên bố là đã đạt.
