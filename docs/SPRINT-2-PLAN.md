# Nhóm 3 — Tình hình dự án và kế hoạch Sprint 2
Cập nhật: 05/10/2026 (Asia/Saigon). Bản tổng hợp được tạo từ Jira trực tiếp, GitHub và mã nguồn; có thể tái tạo khi nguồn thay đổi. Đây là kế hoạch đề xuất, chưa thay đổi lịch, phân công hoặc trạng thái trên Jira.

## 1. Hiện trạng đã xác minh
- Jira N3: 147 issue; 22 Hoàn tất, 2 Đang làm, 123 Cần làm. Con số gồm epic, story, subtask và hướng dẫn, không phải tỷ lệ hoàn thành sản phẩm.
- Sprint 1 đóng lúc 17:22 ngày 04/10; 7 story/task nền tảng N3-1..7 và 15 subtask N3-77..91 đều Hoàn tất theo Jira.
- Sprint 2 — Bàn giao lô, id 2, board 4: đang active, bắt đầu 17:22 ngày 04/10, kết thúc 00:00 ngày 07/10. Goal đang trống.
- Sprint 2 có 10 story / 20 SP: N3-20 và N3-21 Đang làm; 8 story còn lại Cần làm. 23 subtask N3-92..114 vẫn Cần làm và chưa được gán assignee. Story đã có assignee. SP là giá trị Jira, chưa chứng minh đã được team tái ước lượng.
- Sprint 3..8 chưa bắt đầu: tách/gộp, tìm lô phát sinh, thu hồi, giám sát chuỗi lạnh, QR và báo cáo/kiểm tra.
- Nhóm `upstream/main`: `09f0b334` (sau `d2d9c852`); personal `origin/main`: `038b3a2`. So sánh hai nhánh chính (`upstream/main...origin/main`): nhóm có 10 commit chưa có ở personal, personal có 5 commit nhóm chưa có. Đã fetch cả hai remote; chưa merge.
- Local `feat/super-fe` vẫn theo dõi `origin/main`, nhưng working tree có bản viết lại frontend chưa commit. `App.tsx` import `domain/demoScenario`, `views/Gateway`, `views/Workspace`, `world/World` và `world/store` chưa có trong cây hiện tại. Chưa chạy build; các import thiếu khiến bản local chưa phải baseline có thể chạy/nghiệm thu. Giữ nguyên thay đổi local khi đồng bộ.
- Nhánh nhóm mới nhất đã thêm append-only events/API/migration cho N3-21 và chuyển xác thực sang cookie-only, bỏ `X-Session-Token` trong `d2d9c852`; commit `09f0b334` nâng cấp giao diện trang chủ/đăng nhập. N3-20/N3-21 vẫn là Đang làm trên Jira; chưa được coi là Done chỉ vì code đã lên main.
- Backend nhóm hiện có API GET lots và bảng `lots` mới chỉ gồm `id`, `organization_id`, `farm_id`, `name`; chưa có mã lô, sản phẩm, ngày thu hoạch, khối lượng hoặc chủ giữ hiện tại. Luồng harvest/handover của Sprint 2 chưa được Jira đánh dấu hoàn tất.
- Nhánh fork có redesign/demo hash fixture và tài liệu bàn giao. Demo hash/telemetry không chứng minh backend lưu chuỗi sự kiện thật.
- Chưa xác minh được CI của `d2d9c852` hoặc `09f0b334`: trang Actions hiện hiển thị run #3 trên commit `9b35621`; các kết quả CI trước đó chỉ áp dụng cho SHA đã ghi, không chuyển tiếp sang commit mới.
- HANDOFF ngày 03/10 ghi staging chưa chạy redesign đúng bản. Chưa có kiểm tra domain sau hai commit mới; trạng thái staging hiện chưa xác minh.
- Alembic nhóm hiện đi `20260929_03 → 20260930_04 → 20261005_05`. Fork còn migration thay thế `20261001_04` nối trực tiếp sau `20260929_03`; khi nhập fork cần hợp nhất revision graph và kiểm tra database đã triển khai trước khi upgrade.
- Không tìm thấy AGENTS.md trong repo hoặc các thư mục cha được kiểm tra. Đã đọc CONTRIBUTING.md; dùng PR, review chéo, CI xanh, nghiệp vụ nằm trong services.

## 2. Mục tiêu đề xuất
Một tổ chức tạo lô thu hoạch hợp lệ → có sự kiện hash lưu thật → tìm và xem lịch sử → đề nghị bàn giao → bên nhận xác nhận/từ chối → quyền giữ và chuỗi sự kiện cập nhật nguyên tử, không lộ dữ liệu tổ chức khác.

Không đưa tách/gộp, cảm biến live, QR hoặc animation mới vào phạm vi Sprint 2.

## 3. Phạm vi và người phụ trách hiện tại
| Story | Kết quả | Owner Jira hiện tại | SP | Subtask |
|---|---|---|---:|---|
| [N3-20](https://nhom3-k23c.atlassian.net/browse/N3-20) | Mọi thay đổi của lô được ghi thành sự kiện nối tiếp có hash | VU HIEU KIEN | 3 | N3-99, N3-100, N3-101 |
| [N3-21](https://nhom3-k23c.atlassian.net/browse/N3-21) | Không đường nào trong ứng dụng sửa hay xoá được sự kiện đã ghi | Dinh Bach Hop | 1 | N3-102, N3-103 |
| [N3-22](https://nhom3-k23c.atlassian.net/browse/N3-22) | Kiểm tra toàn vẹn chuỗi sự kiện của một lô chỉ ra đúng chỗ đứt mạch | Lâm Tiến Khởi | 3 | N3-104, N3-105, N3-106 |
| [N3-23](https://nhom3-k23c.atlassian.net/browse/N3-23) | Xem dòng thời gian sự kiện của một lô | Nguyễn Ngọc Linh | 2 | N3-107, N3-108 |
| [N3-24](https://nhom3-k23c.atlassian.net/browse/N3-24) | Bàn giao lô sang tổ chức khác ở trạng thái chờ xác nhận | HOANG TRUNG KIEN | 2 | N3-111, N3-112 |
| [N3-25](https://nhom3-k23c.atlassian.net/browse/N3-25) | Bên nhận xác nhận hoặc từ chối bàn giao kèm lý do | DONG QUOC KHANH | 2 | N3-113, N3-114 |
| [N3-31](https://nhom3-k23c.atlassian.net/browse/N3-31) | Khai báo danh mục sản phẩm và đơn vị tính | NGUYEN THANH LONG | 1 | N3-92, N3-93 |
| [N3-32](https://nhom3-k23c.atlassian.net/browse/N3-32) | Ghi nhận lô thu hoạch với mã lô sinh tự động | KIÊN NGUYỄN MẠNH | 3 | N3-94, N3-95, N3-96 |
| [N3-33](https://nhom3-k23c.atlassian.net/browse/N3-33) | Dữ liệu thu hoạch không hợp lệ bị chặn ở máy chủ | THAN TUAN LINH | 1 | N3-97, N3-98 |
| [N3-34](https://nhom3-k23c.atlassian.net/browse/N3-34) | Danh sách lô tổ chức tôi đang giữ, tìm theo mã lô | Triệu Văn Nam | 2 | N3-109, N3-110 |

Tổng 20 SP trên 10 story; không cộng subtask lần nữa. Owner story chịu trách nhiệm phân subtask và bằng chứng nghiệm thu. Phân công cá nhân thêm phải được nhóm thống nhất theo N3-147.

## 4. Việc cần chốt trước khi coding
1. Vũ Hiếu Kiên điều phối baseline: giữ frontend local chưa commit; nhóm `upstream/main` ở `09f0b334`, fork ở `038b3a2` và hai nhánh đã phân kỳ. Tạo snapshot an toàn rồi mới tích hợp; không ghi đè/reset. Ưu tiên backend/auth/RLS nhóm, chỉ giữ UI fork sau khi tương thích và build.
2. Nhóm đã chốt cookie-only trong `d2d9c852` và bỏ `X-Session-Token`; khi tích hợp fork, cập nhật client/test theo hợp đồng này, không khôi phục header bằng cách bỏ test.
3. Chốt dùng lots đang có hay chuyển sang batches trong backlog. Đề xuất mở rộng lots, ghi mapping batches → lots trong API/docs và được nhóm đồng thuận; tránh hai bảng cùng biểu diễn một lô.
4. Tách origin organization khỏi current holder. Ràng buộc farm cùng tổ chức gốc vẫn đúng khi chuyển người giữ. Danh sách lô lọc theo current holder.
5. Chốt migration thống nhất, quyền runtime, enum đơn vị, Decimal khối lượng, UTC thời gian, hash canonical. Tạo test vector chung Python/TypeScript; không coi sắp khóa JSON đơn giản là đủ để tuyên bố tuân RFC 8785.
6. Chính sách đọc bàn giao: bên nhận được xem tối thiểu lô được gửi cho mình trước khi nhận; bên giao xem hồ sơ bàn giao liên quan sau khi chuyển quyền. Phải có policy rõ thay vì mở đọc tất cả tổ chức.
7. Khóa bản ghi lô khi append event hoặc accept/reject; số thứ tự sự kiện duy nhất trong lô, một pending handover/lô bằng unique index. Retry cùng yêu cầu không chuyển quyền hai lần.
8. Role runtime chỉ SELECT/INSERT batch_events; kiểm cả startup bootstrap/default privileges để không vô tình cấp lại UPDATE/DELETE.
9. Chốt mức bảo đảm hash: phát hiện sửa và xóa giữa chuỗi theo AC; việc xóa đuôi/viết lại cả chuỗi cần head/count đáng tin hoặc neo độc lập. Không hứa hash chain đơn thuần chống mọi hành vi DBA.

## 5. Thứ tự triển khai và lịch đề xuất
Sprint 2 kết thúc lúc 00:00 ngày 07/10 (Asia/Saigon); hiện có 2/10 story Đang làm, 8 story Cần làm và toàn bộ 23 subtask chưa bắt đầu/chưa có người nhận. Chưa có bằng chứng đủ để kết luận sẽ hoàn tất 20 SP theo hạn sprint. Đề xuất mốc nghiệm thu đầy đủ 12/10 vẫn cần nhóm thống nhất trên Jira; các mốc bên dưới là dự báo có điều kiện.

| Mốc | Công việc | Điều kiện ra khỏi mốc |
|---|---|---|
| 05/10 | Baseline, CI auth, migration, hợp đồng API/quyền; Long làm N3-92,93 | CI baseline xanh; migration trên DB trống và DB hiện hữu; products dùng chung/admin-only |
| 06/10 | Mạnh Kiên N3-94..96; Tuấn Linh N3-97,98; Hiếu Kiên N3-99..101 | Tạo lô và event trong một transaction; mã unique/retry collision; validation và rollback đạt |
| 07/10 | Bách Hợp N3-102,103; Khởi N3-104..106; Nam N3-109,110 | Runtime cấm sửa/xóa event; kiểm tamper/delete và một event đúng; tìm/lọc/phân trang đúng tenant |
| 08/10 | Ngọc Linh N3-107,108; Trung Kiên N3-111,112; Khánh N3-113,114 | Timeline từ API thật; pending giữ chủ; accept chuyển chủ; reject lưu lý do ≥10 ký tự |
| 09/10 | Tích hợp và test đồng thời, rollback, cross-tenant, regression Sprint 1 | Hai yêu cầu cạnh tranh không tạo hai pending/fork hash/chuyển quyền hai lần |
| 10/10 | Staging đúng SHA, migration, E2E desktop/mobile, đo hiệu năng | AC pass trên domain; đúng phiên bản frontend và API; số đo có dữ liệu/môi trường |
| 11–12/10 | Dự phòng sửa lỗi, review chéo, PO Lê Đình Tuấn nghiệm thu, bàn giao | Mỗi story có PR + CI + bằng chứng staging; chỉ khi đó chuyển Done |

Nếu giữ deadline 06/10: đề xuất chỉ cam kết nền products + harvest/event/validation (N3-31,32,33,20), và chỉ nhận Done khi đủ AC/DoD; phần còn lại cần được nhóm chuyển lịch. Đây là phạm vi cứu tiến độ, chưa đạt toàn bộ mục tiêu bàn giao Sprint 2.

Phụ thuộc trọng yếu: products → lots/harvest + events → append-only/verify → timeline → handover → accept/reject → staging.
Có thể chuẩn bị UI từ API contract trong lúc backend hoàn thiện; không đóng story bằng dữ liệu mock. Không triển khai agents/worktrees song song trong lượt lập kế hoạch này.

## 6. Tiêu chí nghiệm thu bắt buộc
- Products: enum kg/tấn/thùng; tên unique; mọi tenant đọc được; chỉ admin ghi, API role khác 403.
- Harvest: mã 8 ký tự không 0/O/1/I/L, unique DB + retry; test 10000 mã và cưỡng bức collision; hai request đồng thời; khối lượng dương, ngày không tương lai, farm khác tenant 403; mã hiển thị lớn/copy.
- Event: genesis cố định, canonical hash dùng một nguồn thuật toán; đổi key order cùng hash, đổi nội dung khác hash; lô và event cùng commit/rollback; sequence/hash không phân nhánh khi concurrent.
- Append-only: runtime SQL UPDATE/DELETE bị từ chối, INSERT được; không có endpoint sửa/xóa event; CI chạy kiểm quyền và bootstrap không cấp lại.
- Verify: nguyên vẹn, một event, sửa giữa, xóa giữa; đúng vị trí đứt, các event sau bị nghi vấn; 1000 event dưới 1 giây; audit kết quả kiểm tra/thời điểm theo N3-105.
- Timeline: tên tổ chức, thứ tự ổn định; cảnh báo toàn vẹn; 200 event API dưới 200ms, trang dưới 2 giây; không N+1; phân trang trên 500 event.
- Lots list: 20/lượt, cursor với tie-breaker ổn định, mới nhất trước, mã không phân biệt hoa thường, product filter; SQL dưới 300ms/5000 lô, trang dưới 1 giây; xác nhận bàn giao thì biến mất khỏi danh sách người gửi.
- Handover: gửi chính mình bị chặn; chỉ current holder tạo; pending chưa đổi chủ; bên nhận thấy pending; accept/reject chỉ đúng receiver; reject ≥10 ký tự; dữ liệu trạng thái + event + holder nguyên tử.
- E2E hai tổ chức: tạo → gửi → nhận; tạo → gửi → từ chối; thử tổ chức thứ ba; logout/hết phiên quay lại đúng trang; mobile; permission đúng server.
- DoD N3-146: một reviewer khác, test logic mới, CI toàn bộ xanh, dependency scan, AC staging, integrity sau nghiệp vụ, test concurrent khi chạm khối lượng, không secret/PII log, docs cập nhật.

## 7. Nhịp phối hợp
- Mỗi đầu buổi: owner ghi Đã làm / Tiếp theo / Vướng / PR trong đúng ticket. WIP một subtask chính/người.
- Vướng hợp đồng/schema/quyền báo ngay cho Hiếu Kiên; không tự tạo migration chồng nhau.
- PR nhỏ theo story nhưng migration được điều phối theo thứ tự; reviewer khác tác giả, được chỉ định khi nhận việc.
- Mỗi cuối ngày chạy demo luồng đã tích hợp; ghi SHA, link CI và bằng chứng domain.
- Sau khi team đồng thuận: điền Sprint Goal, cập nhật end date/phạm vi, gán 23 subtask, ghi dependency và bằng chứng. Chưa thực hiện những thay đổi Jira này trong lượt lập kế hoạch.

## 8. Nguồn
- [Board N3](https://nhom3-k23c.atlassian.net/jira/software/projects/N3/boards/4)
- [DoD/DoR N3-146](https://nhom3-k23c.atlassian.net/browse/N3-146)
- [Team charter/hướng dẫn N3-147](https://nhom3-k23c.atlassian.net/browse/N3-147) — phần nói Sprint 1 còn mở đã cũ so với metadata sprint mới.
- [Repo nhóm](https://github.com/nhom-3-cnttk23c/truy-xuat-nguon-goc-chuoi-lanh-nong-san)
- [GitHub Actions của nhóm](https://github.com/nhom-3-cnttk23c/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions) — lần đối chiếu này chỉ thấy run #3 trên commit `9b35621`, chưa thấy kết quả cho `d2d9c852`/`09f0b334`.
- [Commit N3-21 và auth cookie-only](https://github.com/nhom-3-cnttk23c/truy-xuat-nguon-goc-chuoi-lanh-nong-san/commit/d2d9c8520a6fd4d73b788875084937d78ab7b318)
- [Commit giao diện trang chủ/đăng nhập](https://github.com/nhom-3-cnttk23c/truy-xuat-nguon-goc-chuoi-lanh-nong-san/commit/09f0b334c9bd1ae1e098cd2f7b9001e9936743c6)
- [Lượt kiểm tra rollout ghi trong HANDOFF](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37006634079) — bằng chứng cũ, không xác nhận tình trạng hiện tại.
- HANDOFF.md và CONTRIBUTING.md tại repo local. Kết quả test cũ chỉ áp dụng SHA ghi trong tài liệu.

## 9. Snapshot toàn bộ Sprint 2
Phần dưới giữ AC/phụ thuộc từ backlog để tra cứu; các dòng “Status theo file” là trạng thái trong bản backlog nguồn, không phải trạng thái Jira hiện tại. Dùng tóm tắt Jira ở mục 1 làm nguồn trạng thái: N3-20/N3-21 Đang làm; 8 story còn lại Cần làm; 23 subtask N3-92..114 Cần làm và chưa gán người.

### N3-20 — Mọi thay đổi của lô được ghi thành sự kiện nối tiếp có hash
Owner: VU HIEU KIEN; parent: N3-9.

Nguồn backlog: S-10  
Loại: Story  
Parent backlog: E-04  
Tầng: Ready  
Ưu tiên: Must  
Owner theo file: cả team

User story: Là cán bộ kiểm tra tôi muốn mọi việc xảy ra với một lô đều được ghi lại theo cách không sửa được về sau để hồ sơ truy xuất là bằng chứng đáng tin, không phải bản kê do một bên tự viết.

Acceptance criteria:

* Khi hệ thống ghi sự kiện thu hoạch, sự kiện chứa hash tính từ nội dung của chính nó và hash của sự kiện liền trước trong cùng lô.
* Sự kiện đầu tiên dùng giá trị khởi đầu cố định đã quy ước.
* Cùng một nội dung cho cùng một hash kể cả khi thứ tự khoá JSON khác nhau.
* Giao dịch thất bại thì không ghi lô thiếu sự kiện hoặc sự kiện thiếu lô.

Dependencies: S-08, K-01  
Non-functional requirements: ghi sự kiện và thay đổi trạng thái lô nằm trong cùng một giao dịch.

### N3-21 — Không đường nào trong ứng dụng sửa hay xoá được sự kiện đã ghi
Owner: Dinh Bach Hop; parent: N3-9.

Nguồn backlog: S-11  
Loại trong file: Story  
Parent backlog: E-04  
Tầng: Ready  
Ưu tiên: Must  
Sprint theo file: 2  
Owner theo file: cả team

User story / mục tiêu: Là cán bộ kiểm tra tôi muốn chắc chắn không ai, kể cả lập trình viên, sửa được sự kiện qua ứng dụng để lời cam kết "không sửa được" không phụ thuộc vào việc mọi người nhớ quy ước

Acceptance criteria:  
Giả sử tài khoản ứng dụng chạy lệnh sửa hoặc xoá trên bảng sự kiện, Khi cơ sở dữ liệu nhận lệnh, Thì từ chối vì thiếu quyền  
Giả sử ai đó gọi API sửa hoặc xoá một sự kiện, Khi máy chủ nhận yêu cầu, Thì không có endpoint nào phục vụ việc đó  
Giả sử người mới vào dự án đọc README, Khi tìm phần quy ước, Thì thấy rõ bảng sự kiện là chỉ-thêm và vì sao

Dependencies: S-10

Non-functional requirements: quyền hạn chế ở cơ sở dữ liệu, không chỉ ở mã nguồn

### N3-22 — Kiểm tra toàn vẹn chuỗi sự kiện của một lô chỉ ra đúng chỗ đứt mạch
Owner: Lâm Tiến Khởi; parent: N3-9.

Nguồn backlog: S-12  
Loại trong file: Story  
Parent backlog: E-04  
Tầng: Ready  
Ưu tiên: Must  
Sprint theo file: 2  
Owner theo file: cả team

User story / mục tiêu: Là cán bộ kiểm tra tôi muốn hệ thống tự phát hiện khi hồ sơ bị sửa lén để tôi biết dữ liệu nào còn đáng tin

Acceptance criteria:  
Giả sử chuỗi sự kiện của một lô nguyên vẹn, Khi chạy kiểm tra, Thì báo lô hợp lệ  
Giả sử ai đó sửa nội dung một sự kiện giữa chuỗi bằng SQL trực tiếp, Khi chạy kiểm tra, Thì hệ thống chỉ ra đúng sự kiện bị sửa và mọi sự kiện sau nó đều bị đánh dấu nghi vấn  
Giả sử ai đó xoá một sự kiện giữa chuỗi, Khi chạy kiểm tra, Thì hệ thống phát hiện đứt mạch tại đúng vị trí đó  
Giả sử một lô mới chỉ có một sự kiện, Khi chạy kiểm tra, Thì vẫn báo hợp lệ chứ không báo lỗi

Dependencies: S-11

Non-functional requirements: kiểm tra một lô có 1000 sự kiện xong dưới 1 giây

### N3-23 — Xem dòng thời gian sự kiện của một lô
Owner: Nguyễn Ngọc Linh; parent: N3-9.

Nguồn backlog: S-13  
Loại trong file: Story  
Parent backlog: E-04  
Tầng: Ready  
Ưu tiên: Must  
Sprint theo file: 2  
Owner theo file: cả team

User story / mục tiêu: Là nhà phân phối tôi muốn xem lô này đã đi qua những bước nào và do ai thực hiện để biết hàng mình nhận có nguồn gốc rõ ràng

Acceptance criteria:  
Giả sử một lô đã qua nhiều bước, Khi tôi mở trang chi tiết lô, Thì thấy các sự kiện xếp theo thứ tự thời gian kèm tên tổ chức thực hiện từng bước  
Giả sử lô vừa được tạo và chỉ có một sự kiện, Khi mở trang, Thì thấy đúng một dòng, không hiện trang trống  
Giả sử chuỗi sự kiện của lô có vấn đề toàn vẹn, Khi tôi mở trang, Thì thấy cảnh báo rõ ràng ở đầu dòng thời gian  
Giả sử lô có 200 sự kiện, Khi mở trang, Thì tải xong dưới 2 giây

Dependencies: S-12

Non-functional requirements: không truy vấn con cho từng sự kiện để lấy tên tổ chức

### N3-24 — Bàn giao lô sang tổ chức khác ở trạng thái chờ xác nhận
Owner: HOANG TRUNG KIEN; parent: N3-9.

Nguồn backlog: S-15  
Loại trong file: Story  
Parent backlog: E-04  
Tầng: Ready  
Ưu tiên: Must  
Sprint theo file: 2  
Owner theo file: cả team

User story / mục tiêu: Là vùng trồng tôi muốn bàn giao lô cho hợp tác xã và việc đó được ghi lại để trách nhiệm về lô chuyển đi rõ ràng, có dấu vết

Acceptance criteria:  
Giả sử tôi đang giữ một lô, Khi tôi tạo bàn giao sang tổ chức khác, Thì sự kiện bàn giao được ghi ở trạng thái chờ xác nhận và lô vẫn thuộc quyền giữ của tôi  
Giả sử lô đang có bàn giao chờ, Khi tôi tạo bàn giao thứ hai cho cùng lô, Thì bị chặn  
Giả sử tôi chọn chính tổ chức mình làm bên nhận, Khi lưu, Thì bị chặn  
Giả sử bàn giao đang chờ, Khi bên nhận xem danh sách chờ của họ, Thì thấy lô đó kèm tên tổ chức tôi

Dependencies: S-13

Non-functional requirements: bàn giao là sự kiện ghi thêm vào chuỗi qua hàm ở T-25, không sửa sự kiện cũ

### N3-25 — Bên nhận xác nhận hoặc từ chối bàn giao kèm lý do
Owner: DONG QUOC KHANH; parent: N3-9.

Nguồn backlog: S-16  
Loại trong file: Story  
Parent backlog: E-04  
Tầng: Ready  
Ưu tiên: Must  
Sprint theo file: 2  
Owner theo file: cả team

User story / mục tiêu: Là hợp tác xã sơ chế tôi muốn việc nhận lô phải có xác nhận của tôi để không ai đẩy trách nhiệm một lô hàng sang tôi mà tôi chưa thực sự nhận

Acceptance criteria:  
Giả sử có bàn giao chờ tôi, Khi tôi xác nhận, Thì quyền giữ lô chuyển sang tôi và một sự kiện xác nhận được ghi tiếp vào chuỗi  
Giả sử tôi từ chối, Khi từ chối kèm lý do, Thì lô vẫn ở chỗ bên giao và lý do được ghi vào chuỗi sự kiện  
Giả sử tôi từ chối mà để trống lý do, Khi bấm, Thì bị chặn  
Giả sử một người khác của tổ chức khác gọi API xác nhận bàn giao không dành cho họ, Khi máy chủ nhận, Thì trả về 403

Dependencies: S-15

Non-functional requirements: chuyển quyền giữ và ghi sự kiện nằm trong cùng một giao dịch

### N3-31 — Khai báo danh mục sản phẩm và đơn vị tính
Owner: NGUYEN THANH LONG; parent: N3-11.

Nguồn backlog: S-07  
Loại trong file: Story  
Parent backlog: E-03  
Tầng: Ready  
Ưu tiên: Must  
Sprint theo file: 2  
Owner theo file: cả team

User story / mục tiêu: Là quản trị hệ thống tôi muốn có danh mục sản phẩm dùng chung để mọi tổ chức gọi cùng một loại nông sản bằng cùng một tên

Acceptance criteria:  
Giả sử tôi là quản trị, Khi thêm sản phẩm với tên và đơn vị tính, Thì sản phẩm xuất hiện trong danh sách chọn của mọi tổ chức  
Giả sử tôi thêm sản phẩm trùng tên, Khi lưu, Thì bị chặn kèm thông báo rõ  
Giả sử tôi là vùng trồng, Khi mở danh mục, Thì chỉ xem được, không sửa được

Dependencies: S-05

Non-functional requirements: đơn vị tính chọn từ danh sách đóng (kg, tấn, thùng), không nhập tự do

### N3-32 — Ghi nhận lô thu hoạch với mã lô sinh tự động
Owner: KIÊN NGUYỄN MẠNH; parent: N3-11.

Nguồn backlog: S-08  
Loại trong file: Story  
Parent backlog: E-03  
Tầng: Ready  
Ưu tiên: Must  
Sprint theo file: 2  
Owner theo file: cả team

User story / mục tiêu: Là vùng trồng tôi muốn ghi nhận mỗi mẻ thu hoạch thành một lô có mã riêng để mọi bước sau này đều tham chiếu được về đúng mẻ này

Acceptance criteria:  
Giả sử đã có thửa và sản phẩm, Khi ghi nhận thu hoạch với khối lượng và ngày hợp lệ, Thì hệ thống tạo lô mới kèm mã lô sinh tự động và hiện mã đó cỡ lớn cho người dùng  
Giả sử hai người cùng ghi nhận thu hoạch trong cùng một khoảnh khắc, Khi cả hai lưu, Thì mỗi người nhận một mã lô khác nhau  
Giả sử tôi gõ lại mã lô vừa nhận vào ô tìm kiếm, Khi tìm, Thì ra đúng lô đó dù tôi gõ chữ thường hay chữ hoa  
Giả sử lô vừa tạo, Khi xem chi tiết, Thì tổ chức đang giữ là tổ chức của tôi và khối lượng còn lại bằng khối lượng thu hoạch

Dependencies: S-06, S-07

Non-functional requirements: mã lô sinh ngẫu nhiên đủ dài, không dùng số thứ tự tăng dần để đối thủ không suy ra sản lượng

### N3-33 — Dữ liệu thu hoạch không hợp lệ bị chặn ở máy chủ
Owner: THAN TUAN LINH; parent: N3-11.

Nguồn backlog: S-09  
Loại trong file: Story  
Parent backlog: E-03  
Tầng: Ready  
Ưu tiên: Should  
Sprint theo file: 2  
Owner theo file: cả team

User story / mục tiêu: Là cán bộ kiểm tra tôi muốn hệ thống không nhận dữ liệu thu hoạch vô lý để hồ sơ truy xuất không chứa số liệu không ai tin được

Acceptance criteria:  
Giả sử ngày thu hoạch ở tương lai, Khi lưu, Thì bị chặn kèm thông báo rõ lý do  
Giả sử khối lượng bằng 0 hoặc âm, Khi lưu, Thì bị chặn  
Giả sử thửa được chọn thuộc tổ chức khác (gửi thẳng qua API), Khi lưu, Thì trả về 403  
Giả sử người dùng bấm lưu hai lần liên tiếp, Khi form đang gửi, Thì lần bấm thứ hai bị bỏ qua và chỉ một lô được tạo

Dependencies: S-08

Non-functional requirements: mọi kiểm tra chạy ở máy chủ; kiểm tra ở trình duyệt chỉ để báo sớm

### N3-34 — Danh sách lô tổ chức tôi đang giữ, tìm theo mã lô
Owner: Triệu Văn Nam; parent: N3-11.

Nguồn backlog: S-14  
Loại trong file: Story  
Parent backlog: E-03  
Tầng: Ready  
Ưu tiên: Should  
Sprint theo file: 2  
Owner theo file: cả team

User story / mục tiêu: Là hợp tác xã sơ chế tôi muốn thấy mọi lô đang nằm ở chỗ tôi và tìm nhanh theo mã để không phải nhớ mã lô trong đầu

Acceptance criteria:  
Giả sử tổ chức tôi đang giữ nhiều lô, Khi mở trang danh sách, Thì thấy lô sắp theo ngày mới nhất trước, mỗi trang 20 lô  
Giả sử tôi gõ một phần mã lô, Khi tìm, Thì ra các lô có mã chứa chuỗi đó  
Giả sử tôi lọc theo sản phẩm, Khi áp bộ lọc, Thì chỉ còn lô của sản phẩm đó  
Giả sử một lô đã bàn giao xong cho tổ chức khác, Khi tôi xem danh sách, Thì lô đó không còn trong danh sách đang giữ của tôi

Dependencies: S-08

Non-functional requirements: trang tải dưới 1 giây với 5000 lô

### N3-92 — Bảng `products` có đơn vị tính kèm migration
Owner: Chưa phân; parent: N3-31.

Nguồn task: T-16  
Parent story: S-07  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Bảng sản phẩm dùng chung, không có `organization_id`, khai báo rõ với lớp truy vấn ở T-12 là bảng không lọc theo tổ chức. Theo mẫu migration ở T-14.

Acceptance criteria:  
Migration tiến và lùi được; tên sản phẩm có ràng buộc unique

Dependencies: T-14

Non-functional requirements: đơn vị tính là kiểu liệt kê ở cơ sở dữ liệu

### N3-93 — Màn hình danh mục sản phẩm dùng chung cho mọi tổ chức
Owner: Chưa phân; parent: N3-31.

Nguồn task: T-17  
Parent story: S-07  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Trang danh sách và form thêm/sửa sản phẩm, chỉ vai trò quản trị được ghi. Dùng lại bố cục ở T-15.

Acceptance criteria:  
Quản trị thêm được; vùng trồng chỉ thấy danh sách, nút thêm không hiện và API ghi trả về 403

Dependencies: T-16

Non-functional requirements: quyền ghi kiểm ở máy chủ, ẩn nút chỉ là tiện lợi

### N3-94 — Bảng `batches` gắn thửa, sản phẩm, tổ chức đang giữ, kèm migration
Owner: Chưa phân; parent: N3-32.

Nguồn task: T-18  
Parent story: S-08  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Bảng lô hàng có mã, thửa, sản phẩm, khối lượng ban đầu, khối lượng còn lại, tổ chức đang giữ, trạng thái. Theo mẫu migration ở T-16.

Acceptance criteria:  
Migration tiến và lùi được; `batches.code` có ràng buộc unique; khối lượng còn lại có ràng buộc không âm

Dependencies: T-16

Non-functional requirements: chỉ mục trên tổ chức đang giữ và trên mã lô

### N3-95 — Hàm sinh mã lô ngắn, không ký tự dễ nhầm, test 10000 mã không trùng
Owner: Chưa phân; parent: N3-32.

Nguồn task: T-19  
Parent story: S-08  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Hàm sinh mã 8 ký tự từ bảng chữ đã bỏ `0 O 1 I L`, dùng nguồn ngẫu nhiên an toàn. Khi trùng (ràng buộc unique bắt được) thì sinh lại. Test sinh 10000 mã trong một vòng lặp và khẳng định không trùng.

Acceptance criteria:  
Test 10000 mã chạy xanh; mã không chứa ký tự trong danh sách cấm

Dependencies: T-18

Non-functional requirements: bảng chữ và độ dài khai báo ở một hằng số duy nhất

### N3-96 — Màn hình ghi nhận thu hoạch, hiện mã lô cỡ chữ lớn
Owner: Chưa phân; parent: N3-32.

Nguồn task: T-20  
Parent story: S-08  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Form chọn thửa, sản phẩm, khối lượng, ngày; sau khi lưu hiện mã lô ở cỡ chữ lớn kèm nút sao chép. Dùng lại bố cục form ở T-15.

Acceptance criteria:  
Ghi nhận xong thì mã lô hiện rõ và sao chép được; kiểm trên staging bằng điện thoại

Dependencies: T-19

Non-functional requirements: người dùng thường ở ngoài đồng dùng điện thoại dưới nắng — chữ to, tương phản cao

### N3-97 — Kiểm tra phía máy chủ: ngày tương lai, khối lượng không dương, thửa của tổ chức khác
Owner: Chưa phân; parent: N3-33.

Nguồn task: T-21  
Parent story: S-09  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Thêm lớp kiểm tra đầu vào cho endpoint tạo lô, trả về danh sách lỗi theo từng trường. Viết test đơn vị cho từng ca. Lớp kiểm tra này là mẫu cho mọi endpoint ghi sau.

Acceptance criteria:  
Ba ca sai đều bị từ chối với mã lỗi và tên trường rõ ràng; ca đúng vẫn tạo được

Dependencies: T-20

Non-functional requirements: thông báo lỗi tiếng Việt, không lộ chi tiết kỹ thuật

### N3-98 — Hiện lỗi tại đúng ô nhập và chặn bấm gửi hai lần
Owner: Chưa phân; parent: N3-33.

Nguồn task: T-22  
Parent story: S-09  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Form đọc danh sách lỗi từ máy chủ và hiện cạnh ô tương ứng; vô hiệu hoá nút gửi trong lúc đang chờ phản hồi. Áp cho form ở T-20 và T-15.

Acceptance criteria:  
Nhập sai thấy lỗi ngay cạnh ô; bấm hai lần chỉ tạo một lô

Dependencies: T-21

Non-functional requirements: cách hiện lỗi dùng chung, không viết lại cho từng form

### N3-99 — Bảng `batch_events` chỉ cho ghi thêm, kèm migration
Owner: Chưa phân; parent: N3-20.

Nguồn task: T-23  
Parent story: S-10  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Bảng sự kiện gắn với lô: loại sự kiện, nội dung dạng JSON, tổ chức và người thực hiện, thời điểm, hash của chính nó, hash sự kiện trước. Theo mẫu migration ở T-18.

Acceptance criteria:  
Migration tiến và lùi được; chỉ mục trên (lô, thời điểm) để truy vấn dòng thời gian nhanh

Dependencies: T-18

Non-functional requirements: cột hash đủ dài cho thuật toán đã chọn ở K-01

### N3-100 — Hàm băm có chuẩn hoá nội dung, test băm hai lần ra cùng hash
Owner: Chưa phân; parent: N3-20.

Nguồn task: T-24  
Parent story: S-10  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Hàm nhận nội dung sự kiện, chuẩn hoá (sắp xếp khoá, định dạng số và ngày cố định, không khoảng trắng thừa) rồi băm cùng hash trước. Đây là chỗ dễ sai nhất của cả hệ thống — xem R-02. Test: băm hai lần cùng nội dung với thứ tự khoá khác nhau ra cùng hash; đổi một ký tự thì hash đổi.

Acceptance criteria:  
Hai test trên xanh; thuật toán và cách chuẩn hoá khai báo ở một chỗ duy nhất

Dependencies: T-23

Non-functional requirements: không tự cài thuật toán băm, dùng thư viện chuẩn của ngôn ngữ

### N3-101 — Ghi sự kiện thu hoạch trong cùng giao dịch với tạo lô
Owner: Chưa phân; parent: N3-20.

Nguồn task: T-25  
Parent story: S-10  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Sửa luồng tạo lô ở T-20 để tạo lô và ghi sự kiện thu hoạch trong một giao dịch, dùng hàm băm ở T-24. Đây là hàm ghi sự kiện dùng chung — mọi sự kiện sau (bàn giao, tách, gộp) đi qua hàm này.

Acceptance criteria:  
Tạo lô thì có đúng một sự kiện thu hoạch; cố ý ném lỗi sau khi tạo lô thì cả lô lẫn sự kiện đều không tồn tại

Dependencies: T-24

Non-functional requirements: hàm ghi sự kiện nhận giao dịch từ bên gọi, không tự mở giao dịch riêng

### N3-102 — Migration thu hồi quyền sửa và xoá trên `batch_events` của tài khoản ứng dụng
Owner: Chưa phân; parent: N3-21.

Nguồn task: T-26  
Parent story: S-11  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Tạo tài khoản cơ sở dữ liệu riêng cho ứng dụng (khác tài khoản chạy migration) và thu hồi UPDATE, DELETE trên `batch_events`. Cập nhật `docker-compose.yml` ở T-01 để ứng dụng dùng tài khoản này.

Acceptance criteria:  
Ứng dụng vẫn ghi được sự kiện; lệnh sửa và xoá bằng tài khoản ứng dụng bị từ chối

Dependencies: T-25

Non-functional requirements: tài khoản migration không dùng để chạy ứng dụng

### N3-103 — Test khẳng định lệnh sửa và xoá bị cơ sở dữ liệu từ chối; ghi quy ước vào README
Owner: Chưa phân; parent: N3-21.

Nguồn task: T-27  
Parent story: S-11  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Test tích hợp chạy lệnh sửa và xoá trực tiếp bằng tài khoản ứng dụng và khẳng định bị từ chối. Thêm mục "Bảng chỉ thêm" vào README giải thích quy ước và lý do.

Acceptance criteria:  
Test xanh trong CI; README có mục quy ước

Dependencies: T-26

Non-functional requirements: test này chạy trong mọi lần CI để phát hiện ai đó vô tình cấp lại quyền

### N3-104 — Hàm kiểm tra chuỗi một lô trả về vị trí sự kiện đầu tiên sai
Owner: Chưa phân; parent: N3-22.

Nguồn task: T-28  
Parent story: S-12  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Đọc sự kiện của lô theo thứ tự, tính lại hash từng cái bằng hàm ở T-24 và so với hash đã lưu, đồng thời kiểm hash trước có khớp không. Trả về hợp lệ, hoặc vị trí đứt mạch đầu tiên kèm loại lỗi (sửa hay thiếu).

Acceptance criteria:  
Chuỗi nguyên vẹn trả về hợp lệ; chuỗi bị sửa trả về đúng vị trí; chuỗi bị xoá một sự kiện trả về vị trí đứt mạch

Dependencies: T-25

Non-functional requirements: đọc theo lô lớn, không đọc từng bản ghi một

### N3-105 — Màn hình cán bộ kiểm tra chạy kiểm tra một lô và xem kết quả
Owner: Chưa phân; parent: N3-22.

Nguồn task: T-29  
Parent story: S-12  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Trang nhập mã lô, bấm kiểm tra, hiện kết quả: hợp lệ, hoặc vị trí và loại lỗi. Chỉ vai trò cán bộ kiểm tra và quản trị thấy trang này.

Acceptance criteria:  
Lô nguyên vẹn hiện dấu hợp lệ; lô bị sửa hiện đúng sự kiện sai

Dependencies: T-28

Non-functional requirements: kết quả kiểm tra được ghi lại kèm thời điểm để đối chiếu về sau

### N3-106 — Kịch bản sửa lén bằng SQL ba ca (sửa, xoá, nguyên vẹn) chạy trong CI
Owner: Chưa phân; parent: N3-22.

Nguồn task: T-30  
Parent story: S-12  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Kịch bản dựng lô có 10 sự kiện, rồi lần lượt: sửa lén một bản ghi giữa chuỗi bằng SQL với tài khoản migration, xoá một bản ghi, và để nguyên; sau mỗi ca chạy kiểm tra và khẳng định kết quả. Đây là bằng chứng cho AC của S-12 — không có kịch bản này thì không ai biết cơ chế có hoạt động không.

Acceptance criteria:  
Ba ca đúng kết quả trong CI; kịch bản chạy lại được không cần dọn tay

Dependencies: T-29

Non-functional requirements: kịch bản dùng tài khoản migration để sửa lén, mô phỏng đúng người có quyền cao

### N3-107 — Truy vấn sự kiện kèm tên tổ chức trong một lượt, không truy vấn con
Owner: Chưa phân; parent: N3-23.

Nguồn task: T-31  
Parent story: S-13  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Một truy vấn nối bảng sự kiện với tổ chức, lọc theo quyền xem qua hàm ở T-12, dùng chỉ mục ở T-23. Đo thời gian với 200 sự kiện.

Acceptance criteria:  
Trả về đúng thứ tự; chạy dưới 200ms với 200 sự kiện; log truy vấn cho thấy đúng một câu lệnh

Dependencies: T-28

Non-functional requirements: phân trang khi lô có hơn 500 sự kiện

### N3-108 — Màn hình dòng thời gian dọc, cảnh báo toàn vẹn ở đầu nếu có
Owner: Chưa phân; parent: N3-23.

Nguồn task: T-32  
Parent story: S-13  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Hiển thị dòng thời gian dọc, mỗi mốc là một sự kiện với loại, thời điểm, tổ chức. Gọi hàm kiểm tra ở T-28 và hiện cảnh báo ở đầu nếu chuỗi có vấn đề.

Acceptance criteria:  
Dòng thời gian hiện đủ sự kiện; lô có vấn đề toàn vẹn hiện cảnh báo rõ; đọc được trên điện thoại

Dependencies: T-31

Non-functional requirements: người dùng thường ở kho hoặc ngoài đồng — bố cục một cột

### N3-109 — Truy vấn phân trang lô theo tổ chức đang giữ, lọc theo sản phẩm
Owner: Chưa phân; parent: N3-34.

Nguồn task: T-33  
Parent story: S-14  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Truy vấn qua hàm ở T-12, có phân trang và bộ lọc sản phẩm, tìm theo mã không phân biệt hoa thường. Dùng chỉ mục ở T-18.

Acceptance criteria:  
Đúng kết quả với ba bộ lọc; chạy dưới 300ms với 5000 lô trong bảng

Dependencies: T-20

Non-functional requirements: phân trang theo con trỏ, không theo số trang, để không lệch khi có lô mới

### N3-110 — Màn hình danh sách có ô tìm theo mã lô và bộ lọc sản phẩm
Owner: Chưa phân; parent: N3-34.

Nguồn task: T-34  
Parent story: S-14  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Trang danh sách là trang chính sau đăng nhập. Mỗi dòng liên kết tới trang chi tiết lô. Dùng lại bố cục danh sách ở T-15.

Acceptance criteria:  
Tìm và lọc hoạt động trên staging; bấm một dòng mở đúng lô

Dependencies: T-33

Non-functional requirements: ô tìm kiếm có độ trễ nhỏ trước khi gọi máy chủ để không gọi mỗi phím

### N3-111 — Loại sự kiện bàn giao ở trạng thái chờ, lô vẫn thuộc bên giao
Owner: Chưa phân; parent: N3-24.

Nguồn task: T-35  
Parent story: S-15  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Thêm loại sự kiện bàn giao và bảng `handovers` theo dõi trạng thái chờ/đã nhận/từ chối. Ghi sự kiện qua hàm ở T-25. Chặn tạo bàn giao thứ hai khi đang có bàn giao chờ.

Acceptance criteria:  
Tạo bàn giao thì có sự kiện chờ và lô chưa đổi chủ; tạo lần hai bị chặn

Dependencies: T-33

Non-functional requirements: ràng buộc unique một bàn giao chờ mỗi lô ở cơ sở dữ liệu, không chỉ kiểm ở mã

### N3-112 — Màn hình tạo bàn giao chọn tổ chức nhận
Owner: Chưa phân; parent: N3-24.

Nguồn task: T-36  
Parent story: S-15  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Nút "Bàn giao" trên trang chi tiết lô mở form chọn tổ chức nhận từ danh sách tổ chức (trừ tổ chức mình) và ghi chú. Dùng lại cách hiện lỗi ở T-22.

Acceptance criteria:  
Tạo bàn giao xong thì lô hiện nhãn "đang chờ xác nhận"

Dependencies: T-35

Non-functional requirements: danh sách tổ chức nhận chỉ hiện tên, không lộ thông tin khác

### N3-113 — Xác nhận chuyển quyền giữ và ghi sự kiện trong cùng giao dịch; từ chối ghi lý do
Owner: Chưa phân; parent: N3-25.

Nguồn task: T-37  
Parent story: S-16  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Hai endpoint xác nhận và từ chối, chỉ bên nhận gọi được. Xác nhận đổi tổ chức đang giữ của lô, cập nhật `handovers`, ghi sự kiện — cùng một giao dịch. Test: ném lỗi sau khi đổi chủ thì mọi thứ được hoàn tác.

Acceptance criteria:  
Xác nhận đổi chủ và có đủ hai sự kiện; từ chối giữ nguyên chủ và có sự kiện từ chối kèm lý do

Dependencies: T-35

Non-functional requirements: kiểm quyền bên nhận ở máy chủ qua middleware T-11

### N3-114 — Màn hình lô chờ tôi xác nhận có nút xác nhận và từ chối
Owner: Chưa phân; parent: N3-25.

Nguồn task: T-38  
Parent story: S-16  
Sprint theo file: 2  
Status theo file: Todo  
Owner theo file: cả team

Công việc: Trang liệt kê bàn giao đang chờ tổ chức mình, có nút xác nhận và nút từ chối mở ô nhập lý do bắt buộc. Số bàn giao chờ hiện trên thanh điều hướng.

Acceptance criteria:  
Bàn giao mới hiện trong danh sách; xác nhận hoặc từ chối xong thì mất khỏi danh sách và lô đổi đúng trạng thái

Dependencies: T-37

Non-functional requirements: lý do từ chối tối thiểu 10 ký tự

