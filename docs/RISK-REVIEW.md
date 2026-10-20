# Rà soát rủi ro dự án (Sprint 8)

Tài liệu này ghi lại kết quả rà soát cho các hồ sơ rủi ro R-01, R-05, R-07, R-08
và R-09. Mỗi mục nêu bằng chứng đã kiểm chứng, kết luận và việc cần làm tiếp.

Ngày rà soát: 21/10/2026. Người phụ trách: Lâm Tiến Khởi.

---

## R-01 — Team bị cuốn vào blockchain (N3-136)

**Biện pháp giảm thiểu theo tài liệu:** quyết định K-01 (N3-4) và bằng chứng lựa
chọn chuỗi hash.

**Bằng chứng đã kiểm chứng**

| Kiểm tra | Kết quả |
| --- | --- |
| Quyết định kiến trúc | `docs/N3-4-INTEGRITY.md` ghi rõ "Không dùng blockchain" kèm lý do: DB là điểm tin cậy tập trung, triển khai đơn giản và chưa có yêu cầu đồng thuận tổ chức |
| Mã nguồn | `backend/app/core/crypto.py` — `hash = SHA256(previous_hash + ":" + RFC8785(content))`, dùng thư viện `rfc8785` |
| Đo hiệu năng | `node backend/tests/integrity.test.js` — khoảng 11,63 ms tạo hash và 6,76 ms kiểm hash cho 1.000 sự kiện |
| Ràng buộc ở tầng DB | Trigger chặn sửa và xoá sự kiện (`trg_events_prevent_update`, `trg_events_prevent_delete`) |

**Kết luận:** biện pháp giảm thiểu đã có và đúng như tài liệu quyết định. Rủi ro
được chấp nhận và theo dõi, không cần hành động thêm.

**Điểm cần giữ nguyên:** tài liệu K-01 tự nêu giới hạn — quản trị viên có thể viết
lại dữ liệu và tính lại hash thì hệ thống không phát hiện. Đây là giới hạn đã biết,
không phải lỗi mới.

---

## R-05 — Đáp án đếm tay bị đếm sai (N3-140)

**Biện pháp giảm thiểu theo tài liệu:** T-53 (N3-128) và bộ mẫu S-39.

**Bằng chứng đã kiểm chứng**

| Tệp đáp án | Ghi chú trong tệp |
| --- | --- |
| `backend/tests/data/lineage-oracle.json` | "Fixed expected sets copied from existing acceptance constants; not computed by traversal. Human review requirement waived by project owner." |
| `backend/tests/data/workflow-lineage-oracle.json` | "Expected sets written explicitly from the 3 -> 6 -> 3 -> 6 diagram. No traversal code generated these sets. Two-human review was waived by the project owner; no signatures claimed." |
| `backend/tests/data/recall-lineage-oracle.json` | Ghi rõ ticket N3-54 và bộ dữ liệu 4 tầng, 3 tổ chức |

**Kết luận — phát hiện cần xử lý:** yêu cầu của T-53 là **hai người đếm độc lập,
ghi tên và ngày đối chiếu vào tệp đáp án**. Thực tế các tệp đáp án ghi rõ việc đếm
tay bị **miễn trừ (waived)** bởi chủ dự án và **không có chữ ký của ai**. Nghĩa là:

1. Biện pháp giảm thiểu của R-05 **chưa được thực hiện**, chỉ được miễn trừ.
2. Bộ dữ liệu mẫu vẫn dùng được để kiểm thử, nhưng độ tin cậy của nó thấp hơn
   mức R-05 giả định.

**Việc cần làm (chọn một trong hai, ghi vào hồ sơ rủi ro):**

- **Phương án A — thực hiện đếm tay:** hai thành viên đếm độc lập bộ mẫu S-39 và
  S-22, ghi tên, ngày đối chiếu vào tệp đáp án; khi hai kết quả lệch thì phải
  chốt lại trước khi dùng làm oracle.
- **Phương án B — ghi nhận chấp nhận rủi ro:** bổ sung vào hồ sơ rủi ro một dòng
  ghi rõ việc miễn trừ do ai, ngày nào, và vì sao chấp nhận được. Hiện tại hồ sơ
  chưa có dòng này.

**Ưu tiên:** Phương án B nhanh hơn và đủ để đóng rủi ro; Phương án A đáng làm trước
khi dùng bộ mẫu làm căn cứ nghiệm thu chính thức.

---

## R-07 — Kiểm khối lượng tách bằng đọc-rồi-ghi (N3-142)

**Biện pháp giảm thiểu theo tài liệu:** T-42 (khoá dòng lô mẹ) và T-43 (test song
song bắt buộc).

**Bằng chứng đã kiểm chứng**

| Kiểm tra | Kết quả |
| --- | --- |
| Khoá dòng lô mẹ (T-42) | `backend/app/services/lineage_service.py` dùng `.with_for_update(of=Lot)` khi tách lô |
| Test song song (T-43) | `tests/test_sprint3_lineage.py::test_concurrent_split_allows_only_one_thirty_from_forty` (20 ca tham số) và `::test_n340_concurrent_split_pytest_asyncio_two_connections` (hai kết nối độc lập) |
| Chạy lặp | Chạy cả hai test **20 lần liên tiếp**: **20/20 lần xanh**, tương đương hơn 400 ca tách song song không một lần vượt khối lượng lô mẹ |

**Kết luận:** biện pháp giảm thiểu đã được kiểm chứng bằng chạy lặp, không chỉ bằng
một lần chạy. Rủi ro được giảm nhưng **chưa nên đóng**, vì kiểm thử chạy trên
PostgreSQL cục bộ chứ không phải staging.

---

## R-08 — Story Next/Later mang SP thô (N3-143)

**Biện pháp giảm thiểu theo tài liệu:** refine ra to hơn dự tính và tính lại kế
hoạch sau Sprint 3.

**Bằng chứng đã kiểm chứng**

- Sáu story phần đệm S-58…S-63 đều ghi "ước lượng thô 3 SP" — cùng một con số cho
  cả sáu story, dù khối lượng thực tế rất khác nhau.
- **Không issue nào trong Jira đang đặt story point** (trường Story Points trống ở toàn
  bộ 151 issue), nên kế hoạch hiện chỉ tồn tại trên sheet.

**Đề xuất cách refine lại theo loại việc**

| Loại story | SP sau khi refine | Lý do |
| --- | --- | --- |
| Chỉ có backend + API + test | 3 | Một bảng, một vài route, test tích hợp |
| Backend + API + màn hình giao diện | 5 | Thêm một panel, một tab, một nút bấm |
| Có migration + bề mặt công khai mới | 5 | Thêm bảng, policy RLS, route công khai, tài liệu |

**Áp dụng cho sáu story phần đệm**

| Story | Nội dung | SP thô | SP sau refine |
| --- | --- | --- | --- |
| S-58 | Trung tâm thông báo | 3 | 5 |
| S-59 | Gửi email thu hồi | 3 | 3 |
| S-60 | Bản đồ hành trình công khai | 3 | 5 |
| S-61 | Công đoạn chế biến | 3 | 5 |
| S-62 | Vật tư đã dùng | 3 | 5 |
| S-63 | Mời thành viên tổ chức | 3 | 5 |
| | **Tổng** | **18** | **28** |

**Kết luận:** ước lượng thô 18 SP thực tế là **28 SP**. Với focus factor 0,5 như
R-09 ghi nhận, 28 SP chỉ tương đương khoảng **14 SP** năng lực thực tế — tức là phần
đệm **không thể nằm trong một sprint**. Cần tính lại kế hoạch Sprint 9 trở đi trước khi
kéo phần đệm vào.

---

## R-09 — Năm người mới chưa quen phối hợp, chờ review và merge nuốt capacity (N3-144)

**Biện pháp giảm thiểu theo tài liệu:** theo dõi thời gian chờ review/merge trong
từng sprint.

**Bằng chứng đã kiểm chứng** (49 pull request, 44 đã merge, lấy từ GitHub)

| Chỉ số | Giá trị |
| --- | --- |
| Trung vị thời gian chờ đến lúc merge | **0,9 giờ** |
| Số PR chờ trên 24 giờ | **6 / 44** (13,6%) |
| Số PR chờ trên 48 giờ | 3 / 44 |
| Số PR chờ trên 72 giờ | 1 / 44 |
| Chờ lâu nhất | 97,1 giờ (PR #33) |

Bốn PR chờ lâu nhất: #33 (97,1 giờ), #20 (67,5 giờ), #8 (57,4 giờ), #37 (47,9 giờ).

**Kết luận:** trung vị rất tốt nên cơ chế hiện tại **không** phải là nút thắt. Vấn đề
nằm ở **đuôi dài**: gần 14% pull request nằm chờ trên một ngày, và một PR chờ gần
bốn ngày. Focus factor 0,5 mà R-09 đang dùng có vẻ là hợp lý, nhưng nếu dồn thêm
một vài PR như vậy thì capacity thực sự của sprint sẽ bị bào mòn.

**Việc cần làm**

1. Xoay vòng review mỗi ngày: mỗi thành viên nhận tối đa một pull request đang mở,
   ưu tiên PR mở lâu nhất trước.
2. Đặt mốc chờ review trong quy tắc nhóm: một pull request không có phản hồi trong
   **24 giờ** thì người phụ trách nhắc lại ở Daily Scrum.
3. Ghi thời gian chờ này vào báo cáo sprint, để R-09 được theo dõi bằng số liệu thật
   thay vì cảm tính.

---

## Rủi ro liên quan đã xử lý ở Sprint 8

- **R-10 (N3-145) — không có DevOps nên staging hỏng giữa sprint:** hai công việc đã
  làm trong Sprint 8 giảm thiểu trực tiếp rủi ro này — sao lưu cơ sở dữ liệu hằng
  đêm kèm diễn tập khôi phục (N3-76) và job kiểm tra toàn vẹn định kỳ (N3-74) phát
  hiện đứt mạch ngay khi nó xảy ra. Việc còn lại là cấu hình SMTP, đặt nơi lưu bản sao
  lưu và diễn tập khôi phục lần đầu trên staging.
- **R-06 (N3-141) — xoá dữ liệu cá nhân làm vỡ chuỗi hash:** pull request #50 đã
  được ghi nhận trong nhánh chính, nên phần quyết định kiến trúc đã có sẵn. Việc còn
  lại của rủi ro này thuộc chủ sở hữu nhiệm vụ đã được gán.
