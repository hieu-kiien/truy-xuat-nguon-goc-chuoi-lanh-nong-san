# Biên bản diễn tập khôi phục (N3-160, AC4)

AC4 của N3-160 yêu cầu: *"chạy diễn tập khôi phục lần đầu và ghi thời gian
khôi phục vào biên bản"*.

Mỗi lần diễn tập ghi một mục ở đây. Workflow
[`.github/workflows/restore-drill.yml`](../.github/workflows/restore-drill.yml)
chạy tự động mỗi tháng và **ghi thêm** biên bản vào issue
`Biên bản diễn tập khôi phục (N3-160)` trong kho này, kèm bằng chứng ở
artifact `restore-drill`.

---

## Quy trình diễn tập

1. Lấy bản sao lưu mới nhất — từ kho bản sao lưu ngoài nếu đã cấu hình
   (`BACKUP_EXTERNAL_BUCKET`), không thì chụp bản mới từ staging.
2. `python scripts/backup.py verify --dump <tệp>` — checksum phải khớp.
3. `python scripts/backup.py drill --dump <tệp> --target <database trống>` —
   khôi phục và **đo thời gian**.
4. `python -m app.jobs.integrity_scanner --once --all` — mọi chuỗi sự kiện
   phải còn hợp lệ (`broken_lots = 0`).

> `broken_lots` khác 0 nghĩa là bản sao lưu đó **không dùng được**. Khi đó
> phải dùng bản ghi cũ hơn và ghi rõ vào biên bản là đã khôi phục từ bản sao
> lưu cũ, mất dữ liệu trong khoảng thời gian đó.

---

## Lần 1 — 2026-10-21

| Mục | Kết quả |
| --- | --- |
| Thời điểm | 2026-10-21 06:43 UTC |
| Bản sao lưu | `agrochain-20261021T064300Z.dump` (237.931 byte, sha256 `d457ccc7…bcf4a9`) |
| Checksum | Khớp |
| **Thời gian khôi phục** | **2,288 giây** (≈ 0,04 phút) |
| Số bảng kiểm tra dòng | 9 / 9 khớp |
| Bảng không khớp | Không có |
| Quét toàn vẹn sau khôi phục | `checked_lots = 35`, **`broken_lots = 0`**, `alerts_raised = 0` |
| Kết quả | **ĐẠT** |

### Nội dung khôi phục được

| Bảng | Số dòng trước khi sao lưu | Số dòng sau khi khôi phục |
| --- | --- | --- |
| `organizations` | 8 | 8 |
| `users` | 8 | 8 |
| `lots` | 35 | 35 |
| `events` | 88 | 88 |
| `shipments` | 0 | 0 |
| `temperature_readings` | 0 | 0 |
| `cold_chain_violations` | 0 | 0 |
| `integrity_checks` | 0 | 0 |
| `recall_orders` | 0 | 0 |

### Phạm vi và giới hạn của lần diễn tập này

Lần diễn tập đầu tiên chạy trên **database kiểm chứng cục bộ**
(`ttcs_s34_tests`, PostgreSQL 16 trong container), chứ chưa chạy trên
database staging, vì hai điều kiện của AC2/AC4 chưa sẵn sàng tại thời điểm
chạy:

1. **Kho bản sao lưu ngoài máy chủ ứng dụng chưa được cấu hình**
   (`BACKUP_EXTERNAL_BUCKET` còn trống), nên bản sao lưu lấy từ database cục
   bộ chứ không phải từ kho ngoài.
2. **Secret của staging chưa nằm trong repository** (`STAGING_DATABASE_URL` và
   các secret còn lại), nên workflow không thể chụp bản sao lưu từ staging.

---

## Lần 2 — 2026-10-21 (đầy đủ, có kho bản sao lưu ngoài)

Lần này chạy **đúng theo đường đi của sự cố**: sao lưu → đẩy ra kho ngoài →
xoá bản local → tải về từ kho → kiểm tra checksum → khôi phục vào database
trống → quét toàn vẹn.

Kho bản sao lưu ngoài là một điểm cuối **tương thích S3 thật** chạy trên
loopback (`moto`), và máy chủ SMTP là một **máy chủ SMTP thật** chạy trên
loopback (`Mailpit`). Cơ chế được kiểm chứng thật; chỉ còn thay địa chỉ và
khoá bằng tài khoản thật của nhà cung cấp.

### AC1 — thư thật đi ra ngoài

| Bước | Kết quả |
| --- | --- |
| Lệnh kiểm tra | `python scripts/check_smtp.py --recipient nong-ho@ictu.edu.vn` |
| Kết quả lệnh | `ok: true`, `sent: true`, `reason: delivered`, `elapsed_ms: 51`, mã thoát `0` |
| Thư có thật trong hộp thư? | **Có** — 1 thư, `From: no-reply@agrochain.local`, `To: nong-ho@ictu.edu.vn`, 674 byte |
| Nội dung thư | Chỉ có câu báo kiểm tra hạ tầng, **không có dữ liệu nghiệp vụ, không có mật khẩu** |

### AC2 + AC4 — bản sao lưu ra kho ngoài rồi khôi phục

| Bước | Kết quả |
| --- | --- |
| 1. Sao lưu | `agrochain-20261021T070238Z.dump`, 283.442 byte, 35 lô, 88 sự kiện |
| 2. Đẩy ra kho ngoài | **3 file** — `.dump`, `.dump.manifest.json`, `.dump.sha256` (bucket `ttcs-backups`, prefix `agrochain`) |
| 3. Xoá toàn bộ bản local | Chỉ còn kho ngoài giữ bản sao lưu |
| 4. Tải về từ kho ngoài | **3 file** — tải kèm manifest và checksum |
| 5. Kiểm tra checksum | **checksum OK** |
| 6. Khôi phục vào database trống | **2,214 giây** |
| 7. Đối chiếu số dòng | **9/9 bảng khớp**, không có bảng không khớp |
| 8. Quét toàn vẹn sau khôi phục | `checked_lots = 35`, **`broken_lots = 0`**, `alerts_raised = 0` |
| Kết quả | **ĐẠT** |

### Lỗi phát hiện trong lần chạy này

Lần chạy đầu **thất bại ở bước 5**: lệnh `download` chỉ tải tệp `.dump`,
**không tải manifest và checksum** đi kèm. Bản sao lưu tải về vì vậy không
kiểm chứng được, và đúng bước này workflow `restore-drill.yml` sẽ dừng khi
chạy trên staging.

Đã sửa trong `backend/scripts/backup.py`: `download_backup_from_external_store`
nay tải kèm `.manifest.json` và `.sha256` nếu kho có chúng, và bỏ bản sao lưu
cục bộ đi thì tệp tải về **không** kiểm chứng được thì báo sai — không âm thầm
chấp nhận. Kiểm thử tương ứng nằm ở
`backend/tests/test_staging_integrations.py` và
`backend/tests/test_backup_scripts.py`.

### Kiểm thử tích hợp chạy lại trong CI

Hai kết nối của staging được kiểm chứng bằng kiểm thử tích hợp chạy trên
loopback, không cần dịch vụ ngoài:

- `backend/tests/test_staging_integrations.py::test_the_application_really_delivers_through_the_smtp_transport`
  — một máy chủ SMTP thật nhận thư mà ứng dụng gửi đi.
- `backend/tests/test_staging_integrations.py::test_a_dump_survives_a_round_trip_through_an_s3_compatible_store`
  — bản sao lưu đi qua kho tương thích S3 thật và trở lại, checksum khớp.

### Còn lại

Những gì lần diễn tập này **chưa** chứng minh, và phải chạy lại trên staging
sau khi cấu hình xong:

- Thời gian khôi phục thật của database staging (bản sao lưu lớn hơn nhiều).
- Khôi phục từ **bucket của nhà cung cấp thật** thay vì điểm cuối trên
  loopback.
- Gửi thư tới **địa chỉ thật** ngoài mạng nội bộ.

**Khi nào đóng được R-10:** sau khi lần diễn tập trên staging chạy được với
`broken_lots = 0` và `GET /health` trả `smtp_configured: true` lẫn
`backup_external_store_configured: true`. Xem mục 4.6 trong
[OPERATIONS.md](OPERATIONS.md).
