# Hướng dẫn đóng góp — TTCS N3

Tài liệu này là **luật làm việc nhóm**. Tất cả 10 thành viên đều phải đọc và tuân thủ.

---

## 1. Quy tắc đặt tên nhánh Git

Mỗi nhánh phải theo format: `<type>/<mô-tả-ngắn-bằng-tiếng-anh>`

| Type | Dùng khi | Ví dụ |
|---|---|---|
| `feature/` | Thêm tính năng mới | `feature/user-login` |
| `fix/` | Sửa lỗi | `fix/login-crash-on-mobile` |
| `docs/` | Cập nhật tài liệu | `docs/update-api-readme` |
| `refactor/` | Cải thiện code, không thêm tính năng | `refactor/clean-auth-service` |
| `chore/` | Config, dependencies | `chore/update-fastapi-version` |

> ❌ **Không được đặt tên:** `nhanh-cua-nam`, `test123`, `fix`, `main2`

---

## 2. Quy tắc viết Commit Message

Format chuẩn: `<type>: <mô tả ngắn gọn bằng tiếng Việt>`

```
feat: thêm đăng nhập bằng email và mật khẩu
fix: sửa lỗi không lưu được session sau khi đăng nhập
docs: cập nhật hướng dẫn chạy backend trong README
refactor: tách logic xác thực ra service riêng
chore: nâng cấp fastapi lên 0.141
```

> ❌ **Không được viết:** `fix bug`, `update`, `aaa`, `done`

---

## 3. Quy trình làm việc (Git Workflow)

```
        main (nhánh chính — chỉ merge khi hoàn chỉnh)
          │
          ├── feature/user-login       ← thành viên A làm
          ├── feature/product-list     ← thành viên B làm
          └── fix/api-cors-error       ← thành viên C sửa
```

**Các bước mỗi ngày:**

```bash
# 1. Cập nhật code mới nhất từ main
git checkout main
git pull origin main

# 2. Tạo nhánh mới cho tính năng bạn làm
git checkout -b feature/ten-tinh-nang

# 3. Code → commit thường xuyên (đừng đợi xong mới commit)
git add .
git commit -m "feat: mô tả những gì bạn vừa làm"

# 4. Push nhánh lên GitHub
git push origin feature/ten-tinh-nang

# 5. Mở Pull Request trên GitHub → nhờ 1 người khác review
```

---

## 4. Quy tắc Pull Request (PR)

- **Tiêu đề PR** phải rõ ràng: `feat: Đăng nhập bằng email`
- **Mô tả PR** phải ghi: làm gì, tại sao, cách test
- PR phải được **ít nhất 1 người review và approve** trước khi merge
- **Không tự merge PR của mình** vào `main`
- Giải quyết hết conflict trước khi yêu cầu review

---

## 5. Quy tắc code

### Backend (Python)
- Chạy lint trước khi commit: `make lint-fix`
- Mỗi endpoint mới phải có ít nhất 1 test tương ứng
- Migration DB: **bắt buộc** dùng `make migration msg='...'`, không sửa DB thủ công

### Frontend (TypeScript/React)
- Không dùng `any` — phải khai báo type rõ ràng
- Gọi API qua `src/services/api.ts` — không fetch trực tiếp trong component
- Component mới đặt trong `src/components/`, trang mới trong `src/pages/`

---

## 6. Cấu trúc thư mục — Đặt file ở đâu?

```
backend/app/
├── api/v1/endpoints/   ← File route mới (vd: users.py, products.py)
├── models/             ← SQLAlchemy model (vd: user.py, product.py)
├── schemas/            ← Pydantic schema request/response
└── services/           ← Business logic (không đặt trong endpoint)

frontend/src/
├── components/         ← UI tái sử dụng (Button, Modal, Table...)
├── pages/              ← Màn hình đầy đủ (LoginPage, DashboardPage...)
├── services/           ← Hàm gọi API
├── hooks/              ← Custom React hooks
├── types/              ← TypeScript interfaces
└── utils/              ← Hàm tiện ích thuần túy
```
