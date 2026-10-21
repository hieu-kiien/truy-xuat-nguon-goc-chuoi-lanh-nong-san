# Sao lưu cơ sở dữ liệu và khôi phục (N3-76)

Tài liệu này mô tả cách sao lưu cơ sở dữ liệu hằng đêm, cách giữ lại 14 bản ghi
gần nhất và cách diễn tập khôi phục để đo thời gian phục hồi.

## 1. Nguyên tắc

| Nguyên tắc | Vì sao |
| --- | --- |
| Bản sao lưu nằm **ngoài máy chủ ứng dụng** | Triển khai lại (redeploy) không được xoá bản sao lưu |
| Dùng `pg_dump --format=custom` | Khôi phục từng phần được, nén sẵn |
| Mỗi bản sao lưu có **checksum SHA-256** | Phát hiện được bản sao lưu hỏng trước khi khôi phục |
| Mỗi bản sao lưu có **manifest** | Ghi số dòng của các bảng nghiệp vụ để chứng minh khôi phục đủ dữ liệu |
| Dùng **quyền quản trị** khi sao lưu | `pg_dump` cần đọc được mọi bảng, kể cả bảng có RLS |
| **Không ghi mật khẩu** vào manifest hay log | Manifest chỉ lưu host, tên database và checksum |

## 2. Sao lưu hằng đêm

### Cách chạy trên máy chủ (cron)

```sh
# 02:15 hằng đêm, giữ 14 bản ghi
15 2 * * * cd /opt/agrochain/backend && BACKUP_KEEP=14 ./scripts/backup.sh >> /var/log/agrochain-backup.log 2>&1
```

Script `backend/scripts/backup.sh` kiểm tra `pg_dump` có trong PATH, tạo bản sao
lưu, rồi xác minh checksum của bản mới nhất. Nếu checksum lệch thì lần chạy
đó thất bại.

### Cách chạy bằng GitHub Actions

Workflow `.github/workflows/nightly-backup.yml` chạy lúc **02:15 UTC mỗi ngày**,
tải bản sao lưu lên artifact (giữ 30 ngày) và có thể chạy tay qua
`workflow_dispatch`.

Cần khai báo các secret trong repository:

| Secret | Ý nghĩa |
| --- | --- |
| `STAGING_DATABASE_URL` | Chuỗi kết nối PostgreSQL của staging |
| `STAGING_DB_USER` | Tên đăng nhập của ứng dụng |
| `STAGING_DB_PASSWORD` | Mật khẩu của ứng dụng |
| `STAGING_DB_ADMIN_USER` | Tên đăng nhập quản trị |
| `STAGING_DB_ADMIN_PASSWORD` | Mật khẩu quản trị |

### Cách chạy bằng tay

```sh
cd backend
python scripts/backup.py backup --directory /var/backups/agrochain --keep 14
python scripts/backup.py list   --directory /var/backups/agrochain
python scripts/backup.py verify --dump /var/backups/agrochain/agrochain-20261021T021500Z.dump
```

## 3. Cấu trúc một bản sao lưu

```
/var/backups/agrochain/
├── agrochain-20261021T021500Z.dump              # dữ liệu
├── agrochain-20261021T021500Z.dump.manifest.json # metadata + số dòng
└── agrochain-20261021T021500Z.dump.sha256        # checksum
```

Nội dung manifest:

```json
{
  "file": "agrochain-20261021T021500Z.dump",
  "created_at": "2026-10-21T02:15:00+00:00",
  "size_bytes": 8412880,
  "sha256": "9f2c…",
  "database_name": "ttcs_staging",
  "database_host": "db.internal",
  "counts": { "lots": 128, "events": 4096, "shipments": 12 }
}
```

## 4. Khôi phục

```sh
cd backend
# Xác minh bản sao lưu còn nguyên
python scripts/backup.py verify --dump /var/backups/agrochain/agrochain-20261021T021500Z.dump

# Khôi phục vào một database trống
python scripts/backup.py restore \
  --dump /var/backups/agrochain/agrochain-20261021T021500Z.dump \
  --target postgresql://user:password@host:5432/ttcs_restored
```

`pg_restore` chạy với `--clean --if-exists` nên có thể khôi phục đè lên một
database đã có dữ liệu.

## 5. Diễn tập khôi phục

Diễn tập là bước bắt buộc để biết thời gian phục hồi thực tế, không chỉ lý
thuyết.

```sh
cd backend
# 1. Tạo database trống để nhận bản khôi phục
createdb ttcs_restore_drill

# 2. Khôi phục rồi tự đối chiếu số dòng với manifest
python scripts/backup.py drill \
  --dump /var/backups/agrochain/agrochain-20261021T021500Z.dump \
  --target postgresql://user:password@host:5432/ttcs_restore_drill
```

Kết quả trả về có `duration_seconds` (thời gian khôi phục), `counts` (số dòng
kỳ vọng và thực tế cho từng bảng) và `passed`. Lệnh trả về mã lỗi khi số dòng
lệch, nên diễn tập thất bại sẽ làm pipeline đỏ.

### Nhật ký diễn tập

Ghi lại kết quả mỗi lần diễn tập vào bảng dưới đây và commit cùng tài liệu:

| Ngày diễn tập | Bản sao lưu | Thời gian khôi phục | Số dòng khớp | Người thực hiện |
| --- | --- | --- | --- | --- |
| _(chưa diễn tập)_ | | | | |

## 6. Kiểm tra chuỗi hash sau khi khôi phục

Bản sao lưu chỉ hữu ích khi chuỗi hash của lô hàng vẫn khớp. Sau khi khôi
phục, chạy lại phép kiểm tra toàn vẹn trên một lô:

```sh
cd backend
python -m app.jobs.integrity_scanner --once --all
```

Lệnh này kiểm tra lại chuỗi sự kiện của **mọi** lô (bỏ qua vòng quay 7 ngày) và
ghi kết quả vào `integrity_checks`. Nếu `broken_lots` bằng 0 thì bản khôi phục
vẫn toàn vẹn.

## 7. Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `pg_dump was not found` | Chưa cài PostgreSQL client tools | `apt-get install -y postgresql-client` |
| `permission denied for table ...` | Đang dùng đúng user ứng dụng | Dùng `MIGRATION_DATABASE_URL` (quyền quản trị) |
| Checksum lệch | Bản sao lưu hỏng hoặc bị sửa | Khôi phục từ bản ghi gần nhất còn tốt |
| `mismatches` không rỗng khi diễn tập | Khôi phục thiếu dữ liệu | Kiểm tra log `pg_restore`, không dùng bản sao lưu này |
| Thư mục sao lưu đầy | Bản sao lưu cũ chưa bị dọn | Chạy `python scripts/backup.py prune --keep 14` |
