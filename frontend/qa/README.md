# Kiểm thử giao diện AgroChain

Có hai môi trường độc lập: preview synthetic để thử giao diện nhanh và production entry với FastAPI/PostgreSQL thật trong CI. Production build không import mock.

## Xem giao diện không cần backend

```sh
cd frontend
npm ci
npm run preview:visual
```

Mở `/preview.html` ở địa chỉ Vite in ra. Banner cho phép mở Gateway, ba vai trò, hai theme và lỗi 503 tổng hợp. CRUD chỉ nằm trong bộ nhớ, mất khi tải lại. Ô mật khẩu chỉ nhận giá trị thử; không nhập mật khẩu thật. Preview không chứng minh auth/RBAC/RLS backend.

## Browser synthetic

```sh
cd frontend
npx playwright install --with-deps chromium
npm test
npm run lint
npm run build
npm run build:preview
npm run test:browser
```

7 cấu hình: desktop light/dark 1440×1000, tablet 1024×768, mobile light/dark 390×844, 320×740 và native reduced motion. 11 bài × 7 = 77 ca: 71 chạy, 6 skip có chủ ý cho bài native reduced motion chỉ áp dụng project tương ứng. Dùng `contextOptions: { reducedMotion: 'reduce' }` để Chromium nhận preference thật.

Ảnh/trace ở `test-results/`, report ở `playwright-report/`. Chưa có pixel baseline được duyệt; các ảnh là bằng chứng để đánh giá bố cục.

## Browser với backend thật

Workflow `.github/workflows/frontend-visual.yml` dựng PostgreSQL 16 database `agrochain_browser_test`, role ứng dụng, migrations và demo allowlist hiện có. `qa/seed_live.py` chỉ chạy khi `CI=true` và tên database đúng; tạo thêm tài khoản thường với password ngẫu nhiên, ghi file quyền 0600 được git-ignore. Không upload/log credential.

`npm run test:live` khởi động FastAPI và entry production trên localhost; không mock fetch. 6 bài × desktop/mobile kiểm tra credential login/reload/logout/401, demo ba role/200/403, tenant records, create/edit/persistence/UUID và truy cập chéo tenant. Trace/network body artifact tắt để tránh lưu credential.

Ảnh ở `live-results/`, report ở `live-report/` qua đường dẫn tuyệt đối từ config. Workflow lưu artifact `agrochain-live-browser-qa`, không chứa file credential. Không chạy seed test vào database thật; dùng CI hoặc database dùng một lần đáp ứng guard.

Để sử dụng app bình thường: `npm run dev` và cấu hình `.env` theo `.env.example`. Demo chỉ hoạt động khi cả FE flag và backend environment/allowlist cho phép; không thêm password demo.

## Kết quả

Browser synthetic đã đạt 71 passed/6 skipped; backend thật 12 passed. CI backend hiện có đạt 16 integration tests. Link run, screenshot và giới hạn kiểm chứng cuối ở [VALIDATION.md](../VALIDATION.md).
