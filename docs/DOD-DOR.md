# Definition of Done và Definition of Ready (N3-146)

Tài liệu này là bản chuẩn hoá DoD/DoR của nhóm, lấy từ tab `DoD-DoR` trong
file backlog và từ [CONTRIBUTING.md](../CONTRIBUTING.md). Mục đích là để mọi
người hiểu một câu hỏi trước khi bắt đầu và trước khi chuyển trạng thái:
**việc này đã xong chưa?**

---

## 1. Definition of Ready (DoR) — trước khi nhận việc

DoR là điều kiện để một việc được kéo vào Sprint. Một việc chưa đạt DoR thì
vẫn có thể tồn tại trong Backlog, nhưng **không được coi là cam kết** và
không nên tự kéo vào Sprint khi chưa thống nhất với nhóm.

| # | Điều kiện | Bắt buộc | Ghi chú |
|---|---|---|---|
| 1 | Có đủ nhỏ để Done trong 1 Sprint | Có | Cắt nhỏ trước khi nhận, không nhận rồi mới chia |
| 2 | Dependency ngoài đã có cam kết | Có | Ghi rõ tên việc phụ thuộc trong mô tả |
| 3 | Có AC viết dạng **Giả sử / Khi / Thì** | Có | Hướng dẫn, không phải bắt buộc với mọi việc kỹ thuật thuần |
| 4 | Đã ước lượng story point bởi chính team | Có | Không dùng SP thô của backlog (hướng dẫn) |
| 5 | Team hiểu story nói gì mà không cần hỏi lại người viết | Có | Hướng dẫn |
| 6 | Story cho team thực tập đã chẻ task con ≤ nửa ngày | Có | Hướng dẫn |

**Hệ quả thực tế:** trong dự án AgroChain, một Story chưa được chẻ task con
vẫn giữ nguyên AC, NFR và phụ thuộc trong mô tả. Người nhận việc **refine
trước khi nhận làm**, không nhận rồi mới hỏi lại.

---

## 2. Definition of Done (DoD) — trước khi chuyển sang "Hoàn tất"

Chuyển trạng thái sang `Hoàn tất` chỉ khi **tất cả** mục dưới đây đạt.
Một mục chưa đạt thì việc còn ở `Đang làm`.

### 2.1. Mục bắt buộc cho mọi thay đổi

| # | Điều kiện | Kiểm chứng |
|---|---|---|
| 1 | Code review đã được duyệt bởi **ít nhất một thành viên khác** | PR có ít nhất 1 Approve, không phải người tự tạo PR |
| 2 | Unit test cho nhánh logic mới; độ phủ trên phần thay đổi không giảm | CI xanh, báo cáo coverage trong artifact |
| 3 | CI xanh: build, lint, typecheck, test | 3 job trong `.github/workflows/ci.yml` đều xanh |
| 4 | Không có secret trong mã nguồn; quét phụ thuộc sạch | `pip-audit` và `npm audit` sạch |
| 5 | AC pass trên **môi trường staging**, không chỉ trên máy cá nhân | Bằng chứng chạy trên `ttcs-frontend-staging.onrender.com` |
| 6 | Không log dữ liệu định danh nông hộ | Không có PII trong log |
| 7 | README cập nhật nếu đổi hành vi công khai hoặc thêm biến môi trường | Diff tài liệu trong PR |

> **Điểm dễ sai nhất:** mục 5. Test xanh trên máy cá nhân **không** thay thế
> được nghiệm thu trên staging. Một PR chỉ có test local mà không có bằng
> chứng staging thì chưa đạt DoD.

### 2.2. Mục bắt buộc theo loại Story

| Loại Story | Điều kiện bổ sung |
|---|---|
| Chạm **sự kiện của lô** | Kiểm tra toàn vẹn chuỗi vẫn báo hợp lệ sau khi chạy |
| Chạm **đồ thị phả hệ** | Có ca kiểm thử với bộ dữ liệu mẫu **có đáp án đếm tay** và ca chu trình |
| Chạm **khối lượng** | Có test **hai giao dịch đồng thời** |

Ba mục này bám theo ba rủi ro đã được ghi nhận trong [RISK-REVIEW.md](RISK-REVIEW.md):
R-03 (bỏ sót lô khi truy xuôi), R-04 (chu trình trong đồ thị phả hệ) và
R-07 (tách lô vượt khối lượng lô mẹ khi hai người thao tác cùng lúc).

---

## 3. Checklist nghiệm thu trước khi chuyển trạng thái

Sao chép checklist này vào bình luận Jira của việc đó:

```text
Đã làm:
Tiếp theo:
Đang vướng (nếu có):
Liên kết nhánh hoặc Pull Request (nếu có):
```

Kèm theo, tự kiểm tra theo thứ tự:

1. [ ] PR đã merge vào `main`, CI xanh trên commit cuối
2. [ ] Có ít nhất 1 Approve từ thành viên khác
3. [ ] SHA chạy trên staging khớp commit đã merge
4. [ ] Luồng nghiệp vụ đã chạy thật trên staging, không có 404/403 sai
5. [ ] Bảng quyền kiểm tra trên desktop và mobile
6. [ ] Jira cập nhật trạng thái và bình luận có bằng chứng

**Không tự đánh dấu "Hoàn tất" mà không có bằng chứng.** Nếu có điều chỉnh
được ghi nhận (ví dụ chấp nhận rủi ro, bỏ một AC), ghi rõ trong bình luận để
nhóm cùng biết.

---

## 4. Liên hệ

- Quy trình nhánh, commit, PR: [CONTRIBUTING.md](../CONTRIBUTING.md)
- Cách dùng Jira hằng ngày: [JIRA-GUIDE.md](JIRA-GUIDE.md)
- Bằng chứng nghiệm thu Sprint 1–4: [ACCEPTANCE.md](ACCEPTANCE.md)
- Rủi ro R-01…R-10: [RISK-REVIEW.md](RISK-REVIEW.md)
