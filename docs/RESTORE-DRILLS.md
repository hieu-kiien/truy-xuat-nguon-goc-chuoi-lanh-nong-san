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

Những gì lần diễn tập này **đã chứng minh**:

- Cơ chế `backup → verify → restore → đo thời gian → đối chiếu số dòng →
  quét toàn vẹn` chạy đúng và tự động hoá được.
- Dữ liệu khôi phục lại **đầy đủ và toàn vẹn**: 9/9 bảng khớp số dòng và
  35 chuỗi sự kiện vẫn xác minh được sau khi khôi phục (`broken_lots = 0`).
- Thời gian khôi phục của một bản sao lưu cỡ 230 KB là **2,3 giây**.

Những gì lần diễn tập này **chưa** chứng minh, và phải chạy lại trên staging
sau khi cấu hình xong:

- Thời gian khôi phục thật của database staging (bản sao lưu lớn hơn nhiều).
- Khôi phục từ kho bản sao lưu **ngoài** máy chủ ứng dụng.
- Khôi phục qua đường đi thật của sự cố: tải bản sao lưu → dựng database
  trống trên staging → khôi phục → `integrity_scanner --once --all`.

**Khi nào đóng được R-10:** sau khi lần diễn tập trên staging chạy được với
`broken_lots = 0` và `GET /health` trả `smtp_configured: true` lẫn
`backup_external_store_configured: true`. Xem mục 4.6 trong
[OPERATIONS.md](OPERATIONS.md).
