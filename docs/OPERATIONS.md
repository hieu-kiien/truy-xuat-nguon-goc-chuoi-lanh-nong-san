# Vận hành hệ thống (R-10, N3-145, N3-160)

Rủi ro R-10: *"Không có DevOps nên staging hỏng giữa sprint không ai sửa nhanh"*. Rủi ro
này không xoá được, nhưng có thể **giảm được**: biết ngay khi staging hỏng, và biết
khôi phục bằng cách nào.

Tài liệu này là bản ghi của bốn việc:

1. Kiểm tra sau khi triển khai.
2. Các job bảo trì chạy nền.
3. Kế hoạch khôi phục khi dữ liệu hỏng.
4. **Cấu hình hạ tầng staging còn thiếu (N3-160).**

---

## 1. Kiểm tra sau khi triển khai

Workflow `.github/workflows/deploy-staging.yml` có hai job:

| Job | Việc |
| --- | --- |
| `deploy-staging` | Gọi webhook của Render nếu có, không thì chờ Render tự triển khai từ GitHub |
| `verify-staging` | Chờ tối đa 20 lần (mỗi lần 20 giây), rồi kiểm tra ba thứ |

`verify-staging` kiểm tra:

1. **`/health` trả `status = ok`** — cơ sở dữ liệu còn sống và migration đã chạy xong.
   Phản hồi còn kèm hai cờ booleans: `smtp_configured` và
   `backup_external_store_configured`. Hai cờ này **không chứa** tên máy chủ,
   tên bucket hay thông tin đăng nhập nào.
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
| Nén dữ liệu nhiệt độ | `python -m app.jobs.telemetry_compactor --once` | Hằng đêm | Gom lần đo cũ hơn 30 ngày thành giờ rồi dọn dòng thô (N3-64) |
| Sao lưu | `python scripts/backup.py backup` | Hằng đêm 02:15 UTC | Sao lưu CSDL, giữ 14 bản ghi, xác minh checksum (N3-76) |

Workflow `.github/workflows/integrity-scan.yml` đã chạy job quét toàn vẹn hằng tuần.
Workflow `.github/workflows/nightly-telemetry-compaction.yml` chạy job nén dữ liệu lúc
02:40 UTC mỗi ngày, sau lần sao lưu lúc 02:15 UTC.

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

---

## 4. Cấu hình hạ tầng staging (N3-160)

Ba mục dưới đây là những gì **còn thiếu** trên staging. Nguyên nhân gốc: R-10 đã được
ghi nhận, phần làm được trong kho mã nguồn đã xong, nhưng ba mục còn lại cần **quyền
của máy chủ** nên không làm được từ code.

| # | Việc | AC | Trạng thái |
| --- | --- | --- | --- |
| 1 | Cấu hình SMTP trên staging | AC1 | Sẵn sàng trong mã, **chờ tài khoản thư** |
| 2 | Nơi lưu bản sao lưu ngoài máy chủ ứng dụng | AC2 | Sẵn sàng trong mã, **chờ bucket** |
| 3 | Biến `PUBLIC_APP_URL` trỏ về địa chỉ thật | AC3 | **Đã khai báo trong `render.yaml`** |
| 4 | Diễn tập khôi phục lần đầu và ghi thời gian | AC4 | **Đã chạy**, xem [RESTORE-DRILLS.md](RESTORE-DRILLS.md) |
| 5 | Cập nhật mục chưa cấu hình trong tài liệu này | AC5 | **Đây là tài liệu này** |

### 4.1. AC3 — `PUBLIC_APP_URL`

`render.yaml` khai báo sẵn:

```yaml
- key: PUBLIC_APP_URL
  value: https://ttcs-frontend-staging.onrender.com
```

Render đồng bộ blueprint từ `render.yaml` khi `main` thay đổi, nên giá trị này được
áp dụng cho service `ttcs-backend-staging` mà không cần sửa tay. Nếu service chưa
bật đồng bộ blueprint, đặt tay trong **Render → service → Environment**:

| Biến | Giá trị |
| --- | --- |
| `PUBLIC_APP_URL` | `https://ttcs-frontend-staging.onrender.com` |

**Kiểm chứng:** mở *Quản lý tổ chức → Mời thành viên*, copy link mời. Link phải bắt
đầu bằng `https://ttcs-frontend-staging.onrender.com/moi-dai-nhiep?token=...`,
không phải `http://localhost:5173/...`.

### 4.2. AC1 — SMTP

Ứng dụng đã hỗ trợ SMTP đầy đủ: khi có `SMTP_HOST`, thư thu hồi và lời mời thành viên
**thực sự đi ra ngoài**; khi không có, thư chỉ nằm trong bảng `email_outbox`.

Thiếu một tài khoản thư. Đặt các biến sau cho service `ttcs-backend-staging`:

| Biến | Giá trị | Ghi chú |
| --- | --- | --- |
| `SMTP_HOST` | ví dụ `smtp.mailtrap.io` | Máy chủ SMTP của nhà cung cấp |
| `SMTP_PORT` | `587` | Cổng TLS |
| `SMTP_USER` | tài khoản SMTP | |
| `SMTP_PASSWORD` | mật khẩu ứng dụng / app password | **Không ghi vào tài liệu trong repo** |
| `SMTP_FROM` | địa chỉ người gửi | Phải là địa chỉ mà nhà cung cấp cho phép gửi |
| `SMTP_USE_TLS` | `True` | |

Các biến `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` khai trong `render.yaml`
với `sync: false` — Render **không** tự ghi đè các biến này, người vận hành điền
trong dashboard.

**Kiểm chứng (bằng chứng AC1):**

```sh
cd backend
python scripts/check_smtp.py --recipient <địa-chỉ-nhận-thử>
```

Script mở kết nối thật, gửi một thư thử không mang dữ liệu nghiệp vụ, rồi in kết
quả. Nó **không bao giờ** in mật khẩu. Thoát với mã `0` nghĩa là máy chủ đã nhận
thư; mã `2` nghĩa là chưa cấu hình `SMTP_HOST`.

Sau khi cấu hình, `GET /health` trả `smtp_configured: true`.

### 4.3. AC2 — Nơi lưu bản sao lưu ngoài máy chủ ứng dụng

**Vì sao cần:** trước đây bản sao lưu chỉ nằm trong artifact của GitHub Actions và
chỉ giữ 30 ngày. Hết 30 ngày là không còn đường khôi phục.

Mã nguồn đã hỗ trợ đẩy bản sao lưu ra **kho tương thích S3** (AWS S3, Backblaze B2,
Cloudflare R2, MinIO) — một nhà cung cấp khác, khác hẳn nơi chạy ứng dụng:

```sh
cd backend
python scripts/backup.py upload --dump <tệp.dump>     # đẩy lên
python scripts/backup.py download --directory ./backups # lấy bản mới nhất
```

Khai báo 5 **secret** của repository (`Settings → Secrets and variables → Actions`):

| Secret | Ví dụ | Bắt buộc |
| --- | --- | --- |
| `BACKUP_EXTERNAL_BUCKET` | `ttcs-backups` | Có |
| `BACKUP_EXTERNAL_ACCESS_KEY_ID` | khoá truy cập | Có |
| `BACKUP_EXTERNAL_SECRET_ACCESS_KEY` | khoá bí mật | Có |
| `BACKUP_EXTERNAL_ENDPOINT` | `https://s3.<nhà-cung-cấp>` | Không (bỏ trống nếu dùng AWS S3) |
| `BACKUP_EXTERNAL_REGION` | `auto` | Không |
| `BACKUP_EXTERNAL_PREFIX` | `agrochain` | Không |

Khi `BACKUP_EXTERNAL_BUCKET` còn trống, workflow `nightly-backup.yml` **không** im
lặng bỏ qua: nó in cảnh báo rõ ràng trong log của workflow.

Lớp bảo vệ thứ hai vẫn còn: artifact của GitHub Actions giữ **90 ngày** (đã tăng từ 30).

### 4.4. AC4 — Diễn tập khôi phục

Workflow `.github/workflows/restore-drill.yml` chạy mỗi tháng vào ngày 1 lúc 03:40 UTC,
và chạy được thủ công (`workflow_dispatch`). Nó:

1. Lấy bản sao lưu mới nhất (từ kho ngoài nếu đã cấu hình, không thì chụp bản mới
   từ staging).
2. `pg_restore` vào một PostgreSQL tạm, đo thời gian khôi phục.
3. So số dòng của các bảng nghiệp vụ với số đo lúc sao lưu.
4. Chạy `integrity_scanner --once --all` để chứng minh mọi chuỗi sự kiện vẫn hợp lệ.
5. Ghi biên bản vào issue **`Biên bản diễn tập khôi phục (N3-160)`** trong kho này và
   tải bằng chứng lên artifact `restore-drill`.

Biên bản các lần chạy: [RESTORE-DRILLS.md](RESTORE-DRILLS.md).

### 4.5. AC5 — Tài liệu này

Mục "4. Cấu hình hạ tầng staging" thay cho bảng "Điều chưa cấu hình được trên staging"
cũ. Mỗi mục đều có biến cần đặt, cách kiểm chứng và lệnh kiểm chứng.

### 4.6. Khi nào R-10 được đóng

R-10 chỉ đóng khi **cả ba** điều sau đạt:

1. `GET /health` trả `smtp_configured: true` và `backup_external_store_configured: true`.
2. `python scripts/check_smtp.py` thoát với mã `0` — thư thật đã đi ra ngoài.
3. Có ít nhất **một** bản sao lưu nằm trong kho ngoài, đã trải về qua diễn tập và
   `broken_lots = 0`.

Cho tới khi đó, R-10 **chưa thể đóng** và phải ghi trong báo cáo rủi ro.

---

## 5. Danh sách kiểm tra khi staging hỏng

```sh
curl -s https://ttcs-backend-staging.onrender.com/health
curl -s https://ttcs-backend-staging.onrender.com/version
cd backend && python scripts/backup.py list --directory <thư mục>
cd backend && python scripts/backup.py download --directory ./backups   # nếu có kho ngoài
cd backend && python scripts/backup.py verify --dump <tệp>
cd backend && python scripts/backup.py restore --dump <tệp> --target <url>
cd backend && python -m app.jobs.integrity_scanner --once --all
```

Không ghi mật khẩu, mã bí mật hay dữ liệu định danh nông hộ vào tài liệu trong repo.
