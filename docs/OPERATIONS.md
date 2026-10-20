# Vận hành hệ thống (R-10, N3-145)

Rủi ro R-10: *"Không có DevOps nên staging hỏng giữa sprint không ai sửa nhanh"*. Rủi ro
này không xoá được, nhưng có thể **giảm được**: biết ngay khi staging hỏng, và biết
khôi phục bằng cách nào.

Tài liệu này là bản ghi của ba việc:

1. Kiểm tra sau khi triển khai.
2. Các job bảo trì chạy nền.
3. Kế hoạch khôi phục khi dữ liệu hỏng.

---

## 1. Kiểm tra sau khi triển khai

Workflow `.github/workflows/deploy-staging.yml` có hai job:

| Job | Việc |
| --- | --- |
| `deploy-staging` | Gọi webhook của Render nếu có, không thì chờ Render tự triển khai từ GitHub |
| `verify-staging` | Chờ tối đa 20 lần (mỗi lần 20 giây), rồi kiểm tra ba thứ |

`verify-staging` kiểm tra:

1. **`/health` trả `status = ok`** — cơ sở dữ liệu còn sống và migration đã chạy xong.
2. **`/version` trả đúng commit SHA** của lần push — staging thực sự phục vụ đúng mã mới,
   không phải bản cũ còn treo.
3. **Đủ các route trong danh sách `expected`** — bản OpenAPI của staging có đúng các
   đường dẫn và phương thức mà bản mới yêu cầu.

Danh sách `expected` đã được mở rộng để **bao phủ cả các route Sprint 6 đến Sprint 8**
(chuỗi lạnh, thu hồi, trung tâm thông báo, mời thành viên, vật tư, công đoạn chế biến).
Trước đó nó chỉ kiểm tra route Sprint 1 đến Sprint 4, nên staging có thể báo xanh trong
khi các tính năng mới chưa lên.

Nếu Render báo triển khai lỗi, job dừng ngay thay vì chờ hết 20 lần.

**Cách dùng khi nghi ngờ staging hỏng:**

```sh
curl -s https://ttcs-backend-staging.onrender.com/health
curl -s https://ttcs-backend-staging.onrender.com/version
curl -s https://ttcs-backend-staging.onrender.com/openapi.json | head -c 400
```

- `health` không trả `ok` → cơ sở dữ liệu hoặc migration đang lỗi.
- `version` trả commit khác → staging chưa được cập nhật, đẩy lại nhánh hoặc gọi webhook.
- `openapi.json` thiếu route → bản triển khai lỗi, xem log Render.

---

## 2. Các job bảo trì chạy nền

Cả ba job chạy bằng **quyền quản trị** (`MIGRATION_DATABASE_URL`), tách khỏi quy trình
web, và ghi log số lượng đã xử lý.

| Job | Lệnh | Lịch | Việc |
| --- | --- | --- | --- |
| Quét toàn vẹn | `python -m app.jobs.integrity_scanner --once` | Hằng tuần | Kiểm tra chuỗi sự kiện của mọi lô, ghi cảnh báo khi có lô đứt mạch (N3-74) |
| Nén dữ liệu nhiệt độ | `python -m app.jobs.telemetry_compactor --once` | Hằng đêm | Ggom lần đo cũ hơn 30 ngày thành giờ rồi dọn dòng thô (N3-64) |
| Sao lưu | `./scripts/backup.sh` | Hằng đêm 02:15 UTC | Sao lưu CSDL, giữ 14 bản ghi, xác minh checksum (N3-76) |

Workflow `.github/workflows/integrity-scan.yml` đã chạy job quét toàn vẹn hằng tuần.
Job nén dữ liệu hiện **chưa có workflow**, cần bổ sung cùng với việc cấu hình SMTP và
nơi lưu bản sao lưu.

**Lưu ý khi chạy job nén dữ liệu:** job chỉ gộp chuyến đã đóng. Chuyến đang chạy giữ
nguyên lần đo thô, vì bộ phát hiện vi phạm tính lại chuỗi từ toàn bộ lần đo.

---

## 3. Kế hoạch khôi phục khi dữ liệu hỏng

Quy trình đầy đủ nằm ở [BACKUP-RECOVERY.md](BACKUP-RECOVERY.md). Tóm tắt:

| Bước | Lệnh |
| --- | --- |
| Xem danh sách bản sao lưu | `python scripts/backup.py list --directory <thư mục>` |
| Xác minh bản sao lưu còn nguyên | `python scripts/backup.py verify --dump <tệp>` |
| Khôi phục vào database trống | `python scripts/backup.py restore --dump <tệp> --target <url>` |
| Diễn tập đầy đủ | `python scripts/backup.py drill --dump <tệp> --target <url database trống>` |
| Kiểm tra chuỗi hash sau khôi phục | `python -m app.jobs.integrity_scanner --once --all` |

Sau khi khôi phục, **luôn** chạy job quét toàn vẹn với cờ `--all`. Nếu `broken_lots` bằng 0
thì bản khôi phục vẫn toàn vẹn; nếu khác 0 thì bản sao lưu đó không dùng được.

### Nếu bản sao lưu hỏng

1. Kiểm tra bản ghi gần nhất còn checksum khớp: `python scripts/backup.py list`.
2. Nếu bản gần nhất hỏng, dùng bản ghi cũ hơn và **ghi rõ vào biên bản** là đã khôi phục
   từ bản sao lưu cũ, mất dữ liệu trong khoảng thời gian đó.
3. Nếu mọi bản ghi hỏng, dựng lại từ seed dữ liệu trình diễn
   (`python -m app.seed_demo`) và chấp nhận mất dữ liệu thật — việc này phải báo trước
   trong nhóm và ghi vào hồ sơ rủi ro R-10.

### Điều chưa cấu hình được trên staging

| Việc | Trạng thái | Ảnh hưởng |
| --- | --- | --- |
| SMTP để gửi thư | Chưa có | Thư thu hồi và lời mời thành viên chỉ nằm trong hộp thư ra `email_outbox` |
| Nơi lưu bản sao lưu ngoài máy chủ ứng dụng | Chưa có | Bản sao lưu chỉ nằm trong artifact của GitHub Actions, giữ 30 ngày |
| `PUBLIC_APP_URL` | Chưa có | Link mời thành viên trỏ về localhost |

Không có ba mục này thì R-10 **chưa thể đóng**: hệ thống vẫn chưa có đường khôi phục
thật trên staging.
