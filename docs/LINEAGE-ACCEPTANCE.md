# Phả hệ mẫu Sprint 3–4

Dữ liệu giả lập, không phải hồ sơ nông sản thật. Bộ mẫu gồm 12 lô, 4 tầng,
3 tổ chức; khối lượng tính bằng kg. Không dùng kết quả API để sinh đáp án.

| Cạnh | Khối lượng | Thao tác |
|---|---:|---|
| R1 → A, B | 40, 30 | tách |
| R2 → C, D | 30, 20 | tách |
| A, C → E | 20, 10 | gộp |
| B → F, G | 10, 15 | tách |
| D, F → H | 10, 5 | gộp |
| E → I, J | 12, 8 | tách |

R1 thu hoạch 100, R2 thu hoạch 80 tại nông trại; bàn giao cho HTX trước
khi tách. E bàn giao từ HTX cho nhà phân phối trước khi tách I/J.
G/H cũng bàn giao cho nhà phân phối. Các thao tác là dữ liệu mô phỏng.

| Lô | Tất cả tổ tiên (không tính chính nó) | Tất cả hậu duệ (không tính chính nó) | Còn lại |
|---|---|---|---:|
| R1 | ∅ | A, B, E, F, G, H, I, J | 30 |
| R2 | ∅ | C, D, E, H, I, J | 30 |
| A | R1 | E, I, J | 20 |
| B | R1 | F, G, H | 5 |
| C | R2 | E, I, J | 20 |
| D | R2 | H | 10 |
| E | A, C, R1, R2 | I, J | 10 |
| F | B, R1 | H | 5 |
| G | B, R1 | ∅ | 15 |
| H | B, D, F, R1, R2 | ∅ | 15 |
| I | A, C, E, R1, R2 | ∅ | 12 |
| J | A, C, E, R1, R2 | ∅ | 8 |

Tổng khối lượng còn lại: 180 kg, bằng hai lô gốc. API bao gồm cả lô
được chọn trong `nodes`, nên số node bằng số tổ tiên/hậu duệ cộng một.

Đáp án trên được soạn bằng cách đọc sơ đồ; chưa có hai người độc lập
ký xác nhận. Mã traversal đã tồn tại trước tài liệu này, vì vậy không
khẳng định đáp ứng điều kiện viết oracle trước mã truy vấn của N3-44.
Chủ dự án đã cho phép bỏ bước chờ hai người nghiệm thu trong phiên làm
việc ngày 11/10/2026. Thay thế bằng đáp án cố định cho cả hai hướng,
kiểm thử API thật và review độc lập bằng agent. Không ghi nhận rằng hai
người đã ký xác nhận; Jira chưa được sửa để phản ánh điều chỉnh này.

Chạy lại bộ mẫu: `python -m app.seed_lineage_demo`, chỉ trong môi trường
development hoặc staging với `DEMO_PASSWORD` được đặt rõ ràng. Seed dùng
kết nối bảo trì, một transaction; không ghi đè dữ liệu đã có. Mã lô
`S34-<nhãn>` và UUID cố định dành riêng cho bộ mẫu.

## Bộ mẫu nghiệp vụ 18 lô (N3-127)

Chạy `python -m app.seed_lineage_demo --workflow` trong môi trường demo
với `DEMO_PASSWORD`. Nông sản Bắp cải xanh; ba thửa thuộc nông trại,
HTX giữ các nguồn trước tách/gộp, đơn vị phân phối giữ các lô gộp trước tách cuối.

```text
R1 (100) -> A1 (50), A2 (50)
R2 (100) -> B1 (50), B2 (50)
R3 (100) -> C1 (50), C2 (50)
A1 + B1 -> M1 (100) -> D1 (40), D2 (60)
A2 + C1 -> M2 (100) -> E1 (50), E2 (50)
B2 + C2 -> M3 (100) -> F1 (30), F2 (70)
```

Tất cả nguồn trung gian còn 0; tổng sáu lô cuối 300 kg. Mỗi cặp lô cuối có hai vùng trồng nguồn tương ứng.
Đáp án 36 tập viết cố định ở `backend/tests/data/workflow-lineage-oracle.json`,
không sinh bằng API/traversal. Test so cả 36 tập và integrity cả 18 lô.
Seed dùng service thật; các service commit savepoint bên trong một giao dịch
bảo trì bên ngoài. Lỗi tại gộp rollback cả thu hoạch, bàn giao và tách trước đó.
Chạy lại giữ nguyên ID/hash, không nhân đôi và không ghi đè nếu bộ mẫu thiếu.

Giữ bộ 12 lô cũ và lịch sử đã trình diễn thay vì xóa trước khi chạy lại.
Đây là lựa chọn bảo toàn bằng chứng, khác câu xóa mẫu cũ trong N3-127.
Không giả hai người đã ký đếm hoặc đáp án tồn tại trước code.
