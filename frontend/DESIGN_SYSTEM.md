# AgroChain — hệ thống thiết kế

Hướng chọn: **Field Signal Atlas × Chain Forensics**. Một không gian địa lý trên nền giấy khoáng, có lớp kiểm chứng kỹ thuật. Mục tiêu là trải nghiệm thị giác thú vị; Field Guide chỉ là tính năng phụ.

## Ngôn ngữ hình ảnh

Map canvas lớn, bố cục bất đối xứng, inspector theo ngữ cảnh; headline serif, chữ giao diện sans, dữ liệu mật mã mono. Xanh nông nghiệp đi cùng màu đất, graphite, frost, amber và đỏ lỗi có tiết chế. SVG nguyên bản cho địa hình sơ đồ, tuyến, vị trí và bằng chứng; không dùng emoji hay bộ UI khác.

| Token | Sáng | Tối | Ý nghĩa |
|---|---|---|---|
| Canvas | `#f1efe7` | `#151c19` | Không gian chung |
| Surface | `#fbfaf6` | `#1b2420` | Inspector và điều khiển |
| Ink | `#17251d` | `#edf2eb` | Nội dung chính |
| Muted | `#5f6b62` | `#a0ada2` | Nhãn phụ |
| Accent | `#315f43` | `#8dbd91` | Hành động và nguồn gốc |
| Frost | `#e0ece9` | `#233a3b` | Telemetry |
| Warning | `#895018` | `#e5ae60` | Nhiệt gần giới hạn |
| Danger | `#9e3e34` | `#e38d7d` | Ngoại lệ/lỗi có nhãn riêng |
| Focus | `#527b59` | `#9bcf9c` | Bàn phím |

Màu không thay thế nội dung trạng thái: ngoại lệ nhiệt, digest mismatch, ancestry broken, lỗi API và 403 có tên/biểu tượng riêng. Bài kiểm tra token đối chiếu tỷ lệ tương phản cho chữ và trạng thái ở hai theme; chưa thay thế kiểm tra màn hình thực.

## Typography và bố cục

Dùng font hệ thống, không tải font từ ngoài. Body 14px, input 16px; nhãn dữ liệu tối thiểu 11px, headline responsive 36–80px. Bố cục reflow thay vì thu nhỏ cả desktop. Khoảng cách 4/8/12/16/24/32/48; radius 7/11/17/24.

Desktop: dock gọn, canvas rộng và inspector. Tablet: các view chuyển sang một hoặc hai cột tùy thông tin. Mobile: dock đáy, menu phiên có logout/chuyển demo, marker gọn và chi tiết HTML đầy đủ; hash chain đứng dọc, biểu đồ nằm trong chiều rộng màn hình. Chỉ bảng dữ liệu có cuộn ngang cục bộ.

## Trải nghiệm từng phân hệ

| Phân hệ | Nội dung thị giác chính | Dữ liệu |
|---|---|---|
| Secure Gateway | Kéo kiện hàng, snap chặng, thử nhiệt/tamper, passport và form | Playground local; login/demo dùng API cũ |
| Trace | Route/camera, vị trí kiện hàng và con trỏ thời gian | Fixture được ghi nhãn |
| Farm Atlas | Map/List/Compare, camera GPS, glyph diện tích, UUID và form inspector | API farms hiện có |
| Cold Chain | Bản đồ + nhiệt/ẩm/GPS nội suy theo thời gian | 4 mẫu fixture; không sensor live |
| Forensics | Seal thật, canonical payload, diff 64 hex/256 bit, replay và ancestry | Web Crypto SHA-256 |
| Security X-Ray | Luồng request và hai miền tenant | HTTP/records thật; tầng nội bộ là mô hình suy từ code |
| Field Guide | Spotlight theo 4 chương, có thể thoát ngay | Local; chương cuối chỉ GET |

## Primitives và kiến trúc CSS

`Icon`, `JourneyMap`, `JourneyScrubber`, `JourneyLens`, `HashCompare`, `CommandPalette`, `DemoGuide`; các primitive CSS button/surface/status/detail-list.

CSS tách thành `tokens`, `base`, `shell`, `gateway`, `gateway-journey`, `visualizations`, `responsive`, `journey`, `evidence`, `atlas`, `motion`. CSS và component cũ không còn import đã gỡ. Không còn `index.css` khổng lồ.

## Chuyển động

| Thời gian | Phản hồi |
|---|---|
| 120–180ms | Hover/focus/press |
| 180–320ms | Marker, state, overlay |
| 420–480ms | Camera và native shared-element transition |
| Khoảng 2.1s / 4 bước | Phát xác minh: mỗi bước tính SHA-256 lại |

Native View Transitions giữ cùng sự kiện khi đổi Không gian → Thời gian → Bằng chứng, có feature detection và fallback tức thời. Con trỏ dùng khoảng cách timestamp thật; tuyến/vị trí/telemetry cùng đọc một mô hình, hash inspector dùng mẫu ghi gần nhất. Nội suy luôn được ghi nhãn.

Motion hữu hạn; chỉ trạng thái đang đợi request có thể lặp. Không trì hoãn API. `prefers-reduced-motion` gỡ choreography/camera transition/spotlight smooth scroll; vẫn giữ điều khiển trực tiếp bằng bàn phím/range. Gateway hủy RAF; replay hủy timer; guide gỡ observer/listener khi cleanup. Không thêm runtime dependency, Canvas, WebGL hay filter toàn màn hình chuyển động.

Xem [REDESIGN_NOTES.md](REDESIGN_NOTES.md) và [VALIDATION.md](VALIDATION.md) để phân biệt tính năng đã viết với kiểm chứng đã chạy.
