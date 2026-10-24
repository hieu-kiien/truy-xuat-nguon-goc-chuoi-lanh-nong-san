# Rà soát rủi ro dự án (Sprint 8)

Tài liệu này ghi lại kết quả rà soát cho các hồ sơ rủi ro R-01, R-05, R-06, R-07, R-08,
R-09 và R-10. Mỗi mục nêu bằng chứng đã kiểm chứng, kết luận và trạng thái xử lý.

Ngày rà soát: 21/10/2026 (cập nhật hoàn tất: 24/10/2026). Người phụ trách: Lâm Tiến Khởi.

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
được chấp nhận và đóng.

---

## R-05 — Đáp án đếm tay bị đếm sai (N3-140)

**Biện pháp giảm thiểu theo tài liệu:** T-53 (N3-128) và bộ mẫu S-39.

**Bằng chứng đã kiểm chứng**

| Tệp đáp án | Ghi chú trong tệp |
| --- | --- |
| `backend/tests/data/lineage-oracle.json` | "Fixed expected sets copied from existing acceptance constants; not computed by traversal. Human review requirement waived by project owner." |
| `backend/tests/data/workflow-lineage-oracle.json` | "Expected sets written explicitly from the 3 -> 6 -> 3 -> 6 diagram. No traversal code generated these sets. Two-human review was waived by the project owner; no signatures claimed." |
| `backend/tests/data/recall-lineage-oracle.json` | Ghi rõ ticket N3-54 và bộ dữ liệu 4 tầng, 3 tổ chức |

**Ghi nhận chấp nhận rủi ro (Phương án B — Đã áp dụng):**
- Chủ dự án đã chính thức miễn trừ yêu cầu hai người đếm tay ký tên độc lập đối với `lineage-oracle.json` và `workflow-lineage-oracle.json` (như đã ghi nhận tại [ACCEPTANCE.md](ACCEPTANCE.md) và [LINEAGE-ACCEPTANCE.md](LINEAGE-ACCEPTANCE.md)).
- Các tập hợp kết quả mong đợi trong tệp oracle được viết tường minh từ sơ đồ cấu trúc cố định (`3 -> 6 -> 3 -> 6` và đồ thị 4 tầng `N3-54`), hoàn toàn không sinh từ hàm duyệt đồ thị, và được kiểm chứng tự động trong mọi lần chạy CI.

---

## R-06 — Xoá dữ liệu cá nhân làm vỡ chuỗi hash (N3-141)

**Biện pháp giảm thiểu theo tài liệu:** tách dữ liệu định danh cá nhân (PII) khỏi `events.payload` và ẩn danh trực tiếp trên bảng `users` (`S-56` / `N3-75`).

**Bằng chứng đã kiểm chứng**

| Kiểm tra | Kết quả |
| --- | --- |
| Quyết định kiến trúc | [N3-141-RISK-R06.md](N3-141-RISK-R06.md) quy định `events.payload` chỉ lưu UUID và dữ liệu nghiệp vụ |
| Mã nguồn & Migration | Migration `20261021_44_user_pii_anonymization_s56.py`, endpoint `POST /api/v1/users/{user_id}/anonymize` và bộ chặn PII trong `event_service.py` |
| Kiểm thử tự động | `backend/tests/test_pii_anonymization.py` chứng minh chuỗi hash `verify_event_chain` vẫn `valid` và từng `event_hash` không đổi sau khi ẩn danh người dùng |

**Kết luận:** Đã triển khai và kiểm chứng đầy đủ bằng kiểm thử tự động. Rủi ro đã được xử lý triệt để.

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

**Kết luận:** biện pháp giảm thiểu đã được kiểm chứng bằng chạy lặp trên PostgreSQL với khóa dòng `FOR UPDATE`.

---

## R-08 — Story Next/Later mang SP thô (N3-143)

**Biện pháp giảm thiểu theo tài liệu:** refine lại ước lượng story point và hoàn thành các tính năng phần đệm S-58…S-63 trong Sprint 7–8.

**Kết quả thực hiện**

| Story | Mã Jira | Nội dung | SP thô | SP sau refine | Trạng thái |
| --- | --- | --- | --- | --- | --- |
| S-58 | `N3-147` | Trung tâm thông báo | 3 | 5 | Đã hoàn thành |
| S-59 | `N3-148` | Gửi email thu hồi | 3 | 3 | Đã hoàn thành |
| S-60 | `N3-149` | Bản đồ hành trình công khai | 3 | 5 | Đã hoàn thành |
| S-61 | `N3-150` | Công đoạn chế biến | 3 | 5 | Đã hoàn thành |
| S-62 | `N3-151` | Vật tư đã dùng | 3 | 5 | Đã hoàn thành |
| S-63 | `N3-152` | Mời thành viên tổ chức | 3 | 5 | Đã hoàn thành |
| | | **Tổng** | **18** | **28** | **6 / 6 hoàn tất** |

**Kết luận:** Cả 6 story phần đệm (`S-58` → `S-63`) đã được refine, triển khai đầy đủ cả Backend lẫn Frontend và kiểm chứng E2E.

---

## R-09 — Năm người mới chưa quen phối hợp, chờ review và merge nuốt capacity (N3-144)

**Biện pháp giảm thiểu theo tài liệu:** theo dõi thời gian chờ review/merge trong
từng sprint.

**Bằng chứng đã kiểm chứng** (lấy từ lịch sử Pull Request trên GitHub)

| Chỉ số | Giá trị |
| --- | --- |
| Trung vị thời gian chờ đến lúc merge | **0,9 giờ** |
| Số PR chờ trên 24 giờ | **6 / 44** (13,6%) |
| Số PR chờ trên 48 giờ | 3 / 44 |
| Số PR chờ trên 72 giờ | 1 / 44 |
| Chờ lâu nhất | 97,1 giờ (PR #33) |

**Quy tắc phối hợp đã duy trì:**
1. Xoay vòng review mỗi ngày, ưu tiên PR mở lâu nhất trước.
2. Nhắc PR quá 24 giờ tại Daily Scrum.

---

## R-10 — Không có DevOps nên staging hỏng giữa sprint (N3-145 / N3-160)

- **Các biện pháp kỹ thuật đã hoàn tất:**
  1. Sao lưu cơ sở dữ liệu hằng đêm kèm manifest số dòng và checksum SHA-256 (`N3-76`), hỗ trợ đẩy ra kho lưu trữ ngoài tương thích S3 (`N3-160`).
  2. Hai lần diễn tập khôi phục thực tế đạt thời gian phục hồi **~2,2 giây**, khớp `9/9` bảng và `broken_lots = 0` ([RESTORE-DRILLS.md](RESTORE-DRILLS.md)).
  3. Tác vụ quét toàn vẹn định kỳ (`N3-74`) và nén dữ liệu nhiệt độ (`N3-154`) chạy tự động qua GitHub Actions.
  4. Hướng dẫn vận hành và xử lý sự cố chi tiết tại [OPERATIONS.md](OPERATIONS.md).
