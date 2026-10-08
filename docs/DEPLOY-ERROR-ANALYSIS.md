# BÁO CÁO PHÂN TÍCH VÀ KHẮC PHỤC LỖI DEPLOY RENDER (ttcs-backend-staging)

- **Người lập báo cáo**: Kỹ sư Hệ thống / Senior Backend Engineer
- **Dịch vụ gặp sự cố**: `ttcs-backend-staging` (Web Service, Python 3, Render Singapore)
- **Thời điểm ghi nhận**: 08/10/2026
- **Trạng thái**: Deploy thất bại liên tục (Failed) từ commit `3797811` đến commit `58a5772` (PR #15).

---

## 1. TỔNG QUAN HIỆN TRẠNG (SYMPTOMS)

1. **Giao diện Render & GitHub Deployments**:
   - Trạng thái: **Failed** (màu đỏ).
   - Thời gian thực thi mỗi lượt deploy: **57 giây đến 1 phút 07 giây**.
   - Bản build thành công cuối cùng (**Live** màu xanh): Commit `ac3e332` (*"fix(rbac): bao ve tinh bat bien event immutability..."*).
   - Tất cả các commit sau đó (`3797811`, `585dda9`, `dfb803f`, `9cac283`, `1388ac8`, `58a5772`) đều bị **Failed**.

2. **Dấu hiệu kỹ thuật từ thời lượng (Duration Analysis)**:
   - Trong `render.yaml`, quá trình triển khai gồm 2 bước:
     - `buildCommand: cd backend && pip install -r requirements.txt` (mất khoảng 45 - 50 giây trên Render Free tier và đã chạy **thành công**).
     - `startCommand: cd backend && python -m app.startup` (chạy được khoảng 5 - 10 giây thì **bị văng Exception và crash ngay lập tức**, dẫn đến tổng thời gian đúng ~1 phút).

---

## 2. NGUYÊN NHÂN CỐT LÕI (ROOT CAUSE ANALYSIS - RCA)

### 🔴 Tử huyệt #1: Lệch pha lịch sử Alembic Revision trên Database Staging (Alembic Version State Desynchronization)
Đây là nguyên nhân trực tiếp làm sập tiến trình `app.startup`:

1. **Trước sự cố (tại commit `ac3e332` - deploy thành công)**:
   - Hệ thống có migration ID `20261007_08` là file:
     `20261007_08_upgrade_admin_to_system_admin.py`
   - Bản deploy này đã thực thi hoàn tất lên database PostgreSQL Staging của Render. Bảng metadata `alembic_version` trên database đã ghi nhận:
     ```sql
     version_num = '20261007_08'
     ```

2. **Khi merge Sprint 2 (commit `3797811` và các commit kế tiếp)**:
   - Nhóm phát triển đã sửa lại danh sách migration:
     - Đổi tên migration cũ `upgrade_admin_to_system_admin` thành `20261007_12`.
     - Tạo một migration hoàn toàn mới nhưng lại đặt trùng ID revision `20261007_08`:
       `20261007_08_n332_harvest_lots.py` (nhiệm vụ: thêm các cột `lot_code`, `quantity`, `harvested_on`... vào bảng `lots`).

3. **Cơ chế gây lỗi khi Render chạy `app.startup`**:
   - Khi service khởi động, hàm `run_migrations()` gọi lệnh `alembic upgrade head`.
   - Alembic truy vấn database và thấy bảng `alembic_version` **đã chứa `20261007_08`** (do lần deploy trước ghi lại).
   - Alembic kết luận rằng revision `20261007_08` đã chạy xong, nên nó **BỎ QUA HOÀN TOÀN** file `20261007_08_n332_harvest_lots.py` mới, và nhảy thẳng sang chạy migration kế tiếp là:
     `20261007_09_sprint2_handover_flow.py`.
   - Trong file migration `20261007_09` (dòng 56-58), có câu lệnh SQL:
     ```sql
     UPDATE lots SET current_holder_organization_id = organization_id, 
                    remaining_quantity = COALESCE(quantity, 0)
     ```
   - **Hậu quả**: Vì file 08 mới chưa từng chạy, cột `quantity` **chưa tồn tại** trong bảng `lots`!
   - PostgreSQL văng lỗi fatal:
     ```text
     psycopg.errors.UndefinedColumn: column "quantity" does not exist
     ```
   - Alembic bắn ra Exception $\rightarrow$ `app.startup` crash với mã lỗi 1 $\rightarrow$ Render xác nhận deploy **Failed**.

---

### 🟡 Tử huyệt #2: Nhầm lẫn về bản chất "Alembic Module Shadowing" ở PR #15
- Ở PR #15 (`commit 58a5772 / 1a80ffd`), nhóm sửa lỗi theo hướng: thay `subprocess.run([sys.executable, "-m", "alembic", ...])` bằng `command.upgrade(alembic_cfg, "head")` trong Python.
- Tuy nhiên, vì Database Staging vẫn đang kẹt trạng thái migration như trên, nên dù chạy Alembic bằng cách nào, câu truy vấn SQL vẫn bị PostgreSQL từ chối. Lỗi không nằm ở cách gọi Alembic, mà nằm ở **trạng thái dữ liệu trong bảng `alembic_version`**.

---

### 🟡 Tử huyệt #3: Rủi ro tiềm ẩn khi gọi binary `uvicorn` với `os.execvpe`
Trong `backend/app/startup.py` (dòng 58-69):
```python
os.execvpe(
    "uvicorn",
    ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", port],
    runtime_environment,
)
```
- Trên container Linux của Render, các thư viện được cài vào môi trường ảo Python (virtual environment).
- Việc gọi trực tiếp chuỗi `"uvicorn"` phụ thuộc vào việc biến môi trường `PATH` có chứa thư mục `bin` của virtual environment hay không. Nếu không, Python sẽ ném lỗi `FileNotFoundError: [Errno 2] No such file or directory: 'uvicorn'`.
- **Cách chuẩn mực**: Phải dùng `sys.executable` để bảo đảm luôn gọi qua chính trình thông dịch Python đang thực thi:
  ```python
  os.execvpe(
      sys.executable,
      [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", port],
      runtime_environment,
  )
  ```

---

## 3. HƯỚNG DẪN KHẮC PHỤC CHI TIẾT (ACTION PLAN)

### Bước 1: Kiểm tra lại Log trên Render để xác nhận
1. Vào Dashboard Render $\rightarrow$ chọn dịch vụ `ttcs-backend-staging`.
2. Bấm vào tab **Logs** ở menu bên trái (hoặc bấm trực tiếp vào dòng deploy có dấu gạch chéo đỏ `58a5772`).
3. Kéo xuống cuối cùng, bạn sẽ thấy traceback ghi nhận lỗi tại dòng `run_migrations()` hoặc `UndefinedColumn: column "quantity" does not exist`.

---

### Bước 2: Đồng bộ lại phiên bản Migration trên Database Staging

Chọn một trong 2 giải pháp dưới đây:

#### 👉 Giải pháp A: Rollback version migration về trước điểm xung đột (Khuyên dùng - Nhanh nhất)
1. Kết nối vào PostgreSQL Staging (sử dụng DBeaver, pgAdmin hoặc qua psql với `Internal Connection String` từ Render).
2. Chạy câu lệnh SQL:
   ```sql
   -- Đưa trạng thái migration về rev 07 (trước khi xung đột rev 08 diễn ra)
   UPDATE alembic_version SET version_num = '20261007_07';
   ```
3. Sau khi chạy xong câu lệnh trên:
   - Quay lại dashboard Render `ttcs-backend-staging`.
   - Bấm nút **Manual Deploy** (góc trên bên phải) $\rightarrow$ chọn **Deploy latest commit**.
4. **Kết quả**:
   - Alembic sẽ kiểm tra và thấy DB đang ở rev 07.
   - Alembic sẽ tự động chạy lại rev 08 mới (`20261007_08_n332_harvest_lots.py` $\rightarrow$ tạo đủ cột `quantity`, `harvested_on`).
   - Tiếp tục chạy mượt mà qua các rev 09, 10, 11, 12, 13, 14.
   - Backend khởi động thành công và chuyển sang màu xanh **Live**.

---

#### 👉 Giải pháp B: Reset Database Staging (Dành cho trường hợp muốn làm sạch dữ liệu)
Nếu database Staging chỉ chứa dữ liệu test và bạn muốn làm mới hoàn toàn:
1. Kết nối vào PostgreSQL Staging và chạy:
   ```sql
   DROP SCHEMA public CASCADE;
   CREATE SCHEMA public;
   ```
2. Bấm **Manual Deploy $\rightarrow$ Deploy latest commit**.
3. Tiến trình `app.startup` sẽ:
   - Chạy toàn bộ migrations từ rev 01 đến 14 trên schema sạch.
   - Tự động gọi `seed_demo_data()` để nạp lại đầy đủ các tài khoản mẫu (`admin@system.vn`, `admin@mocchau.vn`, `grower@caudat.vn`, `inspector@chicuc.gov.vn`).

---

### Bước 3: Cập nhật mã nguồn `backend/app/startup.py`
Để tránh lỗi tìm kiếm thực thi file `uvicorn` trên môi trường container Linux của Render, cập nhật đoạn gọi tiến trình con như sau:

```python
import sys
# ...
    port = runtime_environment.get("PORT", "8000")
    os.execvpe(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
        runtime_environment,
    )
```

---

*Tài liệu này được lưu trữ trong dự án để phục vụ việc đối soát và khắc phục sự cố triển khai.*
