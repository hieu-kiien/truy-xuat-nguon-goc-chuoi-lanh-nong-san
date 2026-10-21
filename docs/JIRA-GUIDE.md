# Cách dùng Jira của nhóm (N3-147)

Tài liệu này là phần "hướng dẫn Jira" và "vai trò nhóm" trong mô tả việc
N3-147, được viết lại thành dạng dùng được hằng ngày trong kho mã nguồn.
Đọc kèm [DOD-DOR.md](DOD-DOR.md) (quy tắc hoàn thành) và
[CONTRIBUTING.md](../CONTRIBUTING.md) (quy trình nhánh và PR).

---

## 1. Mỗi ngày làm việc

| Việc | Ở đâu |
|---|---|
| Xem Sprint đang chạy | Board → `Bảng công việc` (board 4) |
| Mở Story nhóm đã chọn | Bấm mã `N3-xx` trên board, phần **Công việc con** nằm bên trong Story |
| Nhận việc | Sau khi nhóm thống nhất, đặt **Người thực hiện = mình** và chuyển sang `Đang làm` |
| Ghi cập nhật | Bình luận trong đúng việc đó, theo mẫu bên dưới |
| Chuyển trạng thái | `Cần làm` → `Đang làm` → `Hoàn tất` |
| Chọn việc tiếp theo | `Danh sách việc` (issue navigator) → xem Story và các Sprint sau |
| Đưa việc vào Sprint sau | **Chỉ khi nhóm đã thống nhất** |

> **Không cần nhớ mã `N3-123`.** Tìm theo tên tiếng Việt. Mã chỉ để Jira
> liên kết các việc với nhau.

---

## 2. Ba trạng thái, ba nguyên tắc

1. Chỉ chuyển sang `Hoàn tất` khi **đáp ứng DoD** (xem [DOD-DOR.md](DOD-DOR.md)).
2. Nếu bị vướng, **ghi bình luận ngay** trong việc đó để cả nhóm biết — đừng
   để việc im lặng quá một ngày.
3. Không sửa phần mô tả / tiêu chí nghiệm thu chỉ để ghi tiến độ. Tiến độ
   nằm ở bình luận.

---

## 3. Mẫu cập nhật bình luận

```text
Đã làm:
Tiếp theo:
Đang vướng (nếu có):
Liên kết nhánh hoặc Pull Request (nếu có):
```

Ví dụ thật:

```text
Đã làm: Thêm màn hình cấu hình ngưỡng nhiệt độ theo loại sản phẩm, kiểm tra
ngưỡng dưới không được lớn hơn ngưỡng trên ở phía máy chủ.
Tiếp theo: Review và mở Pull Request, chạy CI xanh, nghiệm thu trên staging.
Đang vướng (nếu có): Không.
Liên kết nhánh hoặc Pull Request (nếu có): https://github.com/nhom-3-cnttk23c/truy-xuat-nguon-goc-chuoi-lanh-nong-san/pull/52
```

**Không ghi mật khẩu, mã bí mật hay dữ liệu cá nhân vào bình luận Jira.**

---

## 4. Cách nhận việc và ghi cập nhật

- Nếu **một người phụ trách trọn Story**, gán cả Story cho người đó.
- Nếu **chia cho nhiều người**, gán từng **công việc con** cho người phụ trách
  phần đó, để bảng phản ánh đúng người đang chịu trách nhiệm.
- Cập nhật trường **Người thực hiện** trong Jira sau khi nhóm thống nhất —
  bảng phải phản ánh người thực sự đang làm.

---

## 5. Backlog dưới Sprint 8 nghĩa là gì

Backlog dưới Sprint 8 là các mục **chưa gán sprint**, **không phải** danh
sách bắt buộc làm sau Sprint 8. Có ba nhóm:

| Nhóm | Nội dung | Quy tắc |
|---|---|---|
| **Công việc triển khai** | 58 Story/Spike đã xếp Sprint 1–8, có 59 nhiệm vụ con | Làm theo sprint và quan hệ Epic → Story/Task → Subtask |
| **Tính năng dự phòng** | 6 Story S-58–S-63, mỗi mục 3 SP thô | Chỉ chọn khi có nhu cầu, **đã refine** và còn capacity. Không tự kéo vào sprint, không coi là cam kết |
| **Sổ theo dõi rủi ro** | 10 hồ sơ R-01–R-10 | Theo dõi xuyên sprint, dùng liên kết nhiệm vụ giảm thiểu trong từng hồ sơ. **Nhiệm vụ liên quan Done không tự động làm rủi ro Done** |

### Đối chiếu với kế hoạch gốc

- Đã rà đủ **144 mã nguồn**: 11 Epic, 64 Story/Spike (63 Story + K-01),
  59 task con và 10 rủi ro.
- Jira có thêm: `N3-146` (DoD/DoR), `N3-147` (hướng dẫn này), `N3-148`
  (xác minh staging), và `N3-17` đã đánh dấu bản trùng không dùng.
- `N3-16` là Epic E-08 chính thức; giữ `N3-17` để bảo toàn lịch sử.
- **SP và sprint trong sheet là kế hoạch.** Trạng thái `Todo` trong sheet là
  dữ liệu lúc lập kế hoạch — không dùng để đưa nhiệm vụ đã `Hoàn tất` về
  `Cần làm`.
- Giả định **5 developer** trong sheet cần đối chiếu nhân lực thực tế trước
  khi điều chỉnh capacity.

### Việc phát sinh cần xác minh staging

`N3-148` là việc phát sinh cần xác minh và xử lý theo tiêu chí nghiệm thu;
**ưu tiên trước việc dự phòng**. `R-06` cần kiểm tra quyết định trước
Sprint 5; `R-08` cần hiệu chỉnh capacity sau Sprint 3.

---

## 6. Vai trò nhóm theo Team Charter

| Thành viên | Vai trò trong nhóm | Thời gian/tuần |
|---|---|---|
| Lê Đình Tuấn | Phụ trách sản phẩm | 10 giờ |
| Vũ Hiếu Kiên | Điều phối Sprint, Scrum Master kiêm Trưởng nhóm | 40 giờ |
| Đinh Bách Hợp | Developer, thành viên có năng lực nổi bật | 40 giờ |
| Đồng Quốc Khánh | Developer | 40 giờ |
| Lâm Tiến Khởi | Developer | 40 giờ |
| Hoàng Trung Kiên | Developer | 40 giờ |
| Nguyễn Mạnh Kiên | Developer | 40 giờ |
| Nguyễn Ngọc Linh | Developer | 40 giờ |
| Thân Tuấn Linh | Developer | 40 giờ |
| Nguyễn Thành Long | Developer | 40 giờ |
| Triệu Văn Nam | Developer | 40 giờ |

**Phân công và quyền**

- Vũ Hiếu Kiên hiện là người phụ trách dự án trên Jira.
- Đã kiểm tra: cả 10 thành viên trong Team Charter và anh Lê Đình Tuấn đều
  có thể được chọn làm người thực hiện.
- Story / công việc con được phân công **sau khi nhóm thống nhất**; cập nhật
  Người thực hiện trong Jira để bảng phản ánh đúng người đang chịu trách nhiệm.

---

## 7. Quy tắc hoàn thành (rút gọn)

Trước khi chuyển việc sang `Hoàn tất`, kiểm tra:

- Một thành viên khác đã xem và duyệt thay đổi.
- Kiểm thử phù hợp đã chạy và đạt.
- Việc chạy được trên môi trường thử nghiệm.
- Không đưa mật khẩu, mã bí mật hay thông tin riêng của nông hộ vào mã nguồn
  hay nhật ký.
- Cập nhật hướng dẫn chạy dự án nếu có thay đổi.

Các yêu cầu kiểm tra chi tiết cho chuỗi sự kiện, phả hệ lô và giao dịch đồng
thời nằm trong [DOD-DOR.md](DOD-DOR.md).

> **Lưu ý:** Trạng thái và mục tiêu Sprint phải được kiểm tra **trên bảng
> Jira**. Trước khi bắt đầu mỗi Sprint, thống nhất mục tiêu; gán người phụ
> trách cho các Story / công việc con theo phân công thực tế.

---

## 8. Liên hệ

- Quy tắc DoD/DoR: [DOD-DOR.md](DOD-DOR.md)
- Quy trình Git và PR: [CONTRIBUTING.md](../CONTRIBUTING.md)
- Vận hành hệ thống: [OPERATIONS.md](OPERATIONS.md)
- Rủi ro dự án: [RISK-REVIEW.md](RISK-REVIEW.md)
