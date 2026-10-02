# AgroChain — nghiên cứu trải nghiệm thị giác

> Cập nhật triển khai 2026-10-02: Gateway drag/snap, shared lens/cursor, camera route/GPS, hash/bit diff và replay, tenant membranes và mobile chain đã được viết. Các bảng ý tưởng bên dưới ghi trạng thái lúc nghiên cứu, không phải inventory cuối. Xem REDESIGN_NOTES.md và VALIDATION.md cho trạng thái hiện tại và giới hạn kiểm chứng.


> Gateway đã được mở rộng sau lượt nghiên cứu: route drag/snap, native range/bàn phím, hai simulation độc lập và SHA-256 thật. Xem [GATEWAY_IMPLEMENTATION.md](GATEWAY_IMPLEMENTATION.md) để biết trạng thái triển khai/kiểm thử hiện tại. Các ghi chú về Gateway tĩnh hoặc rail cũ bên dưới là lịch sử trước cập nhật; rail được thay bằng trạng thái auth theo request thật. Shared lens/cursor và native View Transitions đã triển khai ở lượt hoàn thiện; xem inventory cuối.

Ngày: 02/10/2026. Mục tiêu đã được người dùng làm rõ: một frontend React rất đẹp, thú vị khi tương tác và có dấu ấn thị giác. Không lấy diễn thuyết hay tour hướng dẫn làm trung tâm. Hướng người dùng chọn: **bản đồ + pháp chứng dữ liệu**.

## Kết luận và mức độ hoàn thành

React + TypeScript + Vite + CSS hiện tại đủ để xây dựng trải nghiệm này. Chưa thấy bế tắc kỹ thuật buộc phải thay framework. Sự khác biệt cần đến từ bố cục, typography, chất liệu và sự liên tục giữa các biểu diễn dữ liệu; số lượng animation không tự tạo ra chất lượng.

Bản hoàn thiện đã có Gateway, Trace, Atlas Map/List/Compare, Journey, Integrity, Security, palette và guide tùy chọn; có camera, selection map/time/hash chung, SHA-256 thật, replay và diff. Không dùng radial theme reveal hoặc inspector morph FLIP chỉ để trang trí. Research giữ lại ý tưởng và giới hạn truy cập nguồn; trạng thái triển khai/kiểm chứng cuối nằm ở [REDESIGN_NOTES.md](REDESIGN_NOTES.md) và [VALIDATION.md](VALIDATION.md).

## Cách đọc bằng chứng nghiên cứu

- **Đọc trang:** nội dung công khai, mô tả hoặc code lấy được. Không đồng nghĩa đã vận hành sản phẩm.
- **Ảnh/index:** ảnh tìm kiếm hoặc metadata/gallery; chỉ dùng cho giả thuyết bố cục, không suy ra usability đã được kiểm nghiệm.
- **Mô tả recording:** đọc mô tả tương tác; chưa phát/xem toàn bộ video.
- **Không truy cập:** lỗi, trang không có nội dung trích xuất hoặc bị giới hạn. Không tính là đã kiểm chứng hình ảnh/flow.

Các nhận xét ở dưới là nguyên tắc rút ra và quyết định của AgroChain. Design concept trên Dribbble/Behance không phải bằng chứng về độ hiệu quả của một sản phẩm đang chạy. Các gallery/font/library phải kiểm tra giấy phép từng asset trước khi đưa asset vào repo.

## Nguồn thị giác và sản phẩm

Chi phí trong bảng là ước lượng của **cách thích nghi cho AgroChain**, không phải benchmark của website nguồn. T = thấp; V = vừa. “Chọn” nghĩa là chọn nguyên tắc, chưa có nghĩa hiệu ứng đã hoàn thành trong code.

| # | Nguồn / trang | Bằng chứng và điều đáng học | Áp dụng cho AgroChain | Kỹ thuật / chi phí | Rủi ro tiếp cận | Quyết định |
|---:|---|---|---|---|---|---|
| 1 | [Mobbin — Map](https://mobbin.com/explore/mobile/screens/map) | Index công khai có nhóm Google Maps/Lyft; bản đồ và sheet giữ địa điểm trong ngữ cảnh. Full flows có giới hạn truy cập. | Atlas mobile | SVG + sheet HTML; T | Marker nhỏ, chỉ hover | Chọn nguyên tắc; chưa xác nhận full flow |
| 2 | [Mobbin — Inventory](https://mobbin.com/explore/web/screens/inventory-management-dashboard) | Nguồn được tìm ở inventory lượt đầu; cần tái kiểm chứng screenshot. | CRUD list | Semantic table; T | Cột dày, action ẩn | Chờ kiểm chứng |
| 3 | [Refero Styles — Factory](https://styles.refero.design/style/13d6fc89-eba2-4724-ac37-20f4f2e5efec) | Đọc trang style công khai. Figure/ground sáng–tối và khoảng trống tạo chiều sâu. Đây là diễn giải của Refero. | Forensics dark | Surface tokens, typography; T | Mono dày hoặc contrast quá gắt | Chọn khoảng trống/tương phản, không sao chép palette |
| 4 | [Refero — The Outsiders](https://refero.design/screens/28e8e3b2-e7f9-4e5c-828c-97ecdd21c456) | Trang trả không có nội dung trích xuất. | Timeline candidate | Chưa quyết định | Chưa đánh giá | Không dùng làm bằng chứng |
| 5 | [SaaSFrame — Visitors Realtime Map](https://www.saasframe.io/examples/visitors-realtime-map) | Đọc mô tả công khai: canvas lớn, cụm vị trí, panel nổi nhỏ. Screenshot/Figma đầy đủ bị giới hạn. | Trace canvas | SVG + overlay; T | Visual thống trị che controls | Chọn hierarchy, bỏ yêu cầu globe 3D |
| 6 | [SaaSFrame — Unkey Roles](https://www.saasframe.io/examples/unkey-roles) | Đọc trang công khai; quyền theo vai trò là thông tin cần đọc trực tiếp. | Security permission matrix | Table + selected row; T | Checkmark không có chữ | Chọn |
| 7 | [Page Flows — Crisp login](https://pageflows.com/post/desktop-web/logging-in/crisp/) | Đã thử mở; không truy cập được recording ở lượt này. | Gateway candidate | Native form; T | Animation thay feedback thật | Chờ, không tuyên bố đã xem flow |
| 8 | [Page Flows — Dashboard patterns](https://pageflows.com/resources/dashboard-design/) | Đã tìm/thử mở; lỗi truy cập. | Task navigation candidate | Chưa quyết định | Chưa đánh giá | Chờ |
| 9 | [Rerun — Maps](https://rerun.io/blog/maps) | Đọc bài chính thức về kết hợp dữ liệu địa lý với các modality; không xem hết video nhúng. | Map/time selection chung | Shared selectedEvent + SVG; V | Nhiều vùng phản ứng gây quá tải | Chọn dữ liệu liên kết, không cài SDK |
| 10 | [Linear](https://linear.app/) | Đọc trang sản phẩm công khai; hierarchy ít nhiễu là đối trọng với canvas biểu cảm. Không test app signed-in. | Dock/palette/shell | CSS + modal; T | Điều hướng ẩn hoặc chữ nhỏ | Chọn nguyên tắc |
| 11 | [Xsupra — product image](https://xsupra.io/images/header.png) | Mở ảnh sản phẩm; index mô tả field/map/weather. Chưa vận hành app. | Atlas layers | Local basemap + inspector; V | Suy diễn NDVI không có dữ liệu | Chọn cấu trúc không gian; không dựng NDVI giả |
| 12 | [Dribbble — Emu Smart Farm](https://dribbble.com/shots/26874392-Emu-AgriTech-Smart-Farm-Monitoring-Dashboard) | Ảnh tìm kiếm/mô tả concept: đồng ruộng là vật thể chủ đạo, neutral ấm. | Trace/Farm art direction | Layered SVG; V | Trang trí che dữ liệu | Chọn chất liệu và tỷ lệ; không copy model 3D |
| 13 | [Dribbble — Emu Mobile](https://dribbble.com/shots/27439937-Emu-Agritech-Mobile-App-Version) | Ảnh/index concept; cần bản mobile riêng. | Atlas mobile | Bottom sheet + canvas ngắn; T | Squeezed desktop | Chọn nguyên tắc responsive |
| 14 | [Behance — Cold Chain](https://www.behance.net/gallery/185185679/Cold-Chain-Management-Dashboard-UI-Design) | Đọc trang case concept; ngữ cảnh vận chuyển giúp số nhiệt độ có ý nghĩa. | Journey | SVG trace + event list; T | Confuse sensor/integrity | Chọn liên kết thời gian, hai loại trạng thái riêng |
| 15 | [Behance — Logistics Platform](https://www.behance.net/gallery/232887965/SaaS-Logistics-Management-Platform) | Đọc mô tả: vehicle map, cargo/driver detail. Không test hệ thống thật. | Route inspector | Canvas + metadata HTML; T | Claim live khi fixture | Chọn bố cục; nhãn mô phỏng |
| 16 | [Awwwards — Map collection](https://www.awwwards.com/awwwards/collections/maps-geolocation-streetview/) | Index tuyển tập; giúp mở rộng tìm kiếm spatial navigation. | Map interaction candidates | SVG focus/zoom; V | Map-only navigation | Chọn hướng nghiên cứu, không copy site |
| 17 | [Awwwards — Google Cloud infrastructure map](https://www.awwwards.com/inspiration/data-visualization-location-map) | Search index; mở trực tiếp timeout. | Spatial overview candidate | SVG thay WebGL; V | Nặng và motion lớn | Chờ xem trực tiếp |
| 18 | [Awwwards — Kombustiveis map](https://www.awwwards.com/inspiration/interactive-map-experience-kombustiveis-by-kuantokusta) | Search index; chưa kiểm chứng live interaction. | Atlas candidate | Chưa chọn implementation | Chưa đánh giá | Chờ |
| 19 | [SiteInspire — Unusual Layout](https://www.siteinspire.com/) | Đọc index, nhóm typographic/grid/unusual layout. | Bố cục bất đối xứng | CSS grid; T | Thứ tự thị giác khác DOM | Chọn nguyên tắc; giữ DOM logic |
| 20 | [SiteInspire — Surfer’s Journal Archives](https://www.siteinspire.com/website/13639-the-surfers-journal-archives) | Mở entry cụ thể; chưa thao tác website nguồn. Editorial archive là hướng tham khảo cho evidence collection. | Event evidence archive | Typography + list detail; T | Kiểu chữ trang trí giảm đọc | Candidate, chưa chốt visual |
| 21 | [Land-book — ClearFlow](https://land-book.com/websites/91332-clearflow) | Đọc entry template; tham khảo khoảng thở của bố cục light. | Warm light shell | CSS tokens; T | Contrast nhạt | Chọn nguyên tắc, không dùng template |
| 22 | [Godly / Recent](https://recent.design/) | Godly root chuyển hướng đến Recent khi kiểm tra; đã đọc gallery. Không suy ra toàn bộ thương hiệu đổi tên. | Visual hierarchy/material candidates | Static surface layers; T | Visual ornament quá mức | Candidate; chưa chọn asset |
| 23 | [Lapa Ninja — Rerun](https://www.lapa.ninja/post/rerun/) | Đọc entry; mở rộng từ gallery sang tài liệu Rerun chính thức. | Scientific spatial UI | SVG + annotated metrics; T | Chart không có text | Chọn cách liên kết spatial/data |
| 24 | [Lapa Ninja — Thingness](https://www.lapa.ninja/post/thingness/) | Search index mô tả experimental storytelling; chưa kiểm chứng live site. | Editorial transitions candidate | Một lần reveal; T | Scroll hijack | Chờ; không dùng scroll hijack |

Tồn tại 24 mục trong sổ nguồn, nhưng các mục “Chờ/không truy cập” không được tính như 24 màn hình đã xem trực tiếp. Yêu cầu khảo sát đầy đủ nhiều flow từ từng gallery, đặc biệt Page Flows/Refero, vẫn chưa đóng nếu không truy cập được nội dung đó. Không dùng số lượng URL để giả định đã hoàn thành toàn bộ research.

## Nguồn chuyển động và code

| # | Nguồn / trang | Bằng chứng / nguyên tắc | Feature, technique và chi phí dự kiến | Rủi ro / fallback | Sẽ dùng? |
|---:|---|---|---|---|---|
| 1 | [60fps — Family sequence of sheets](https://60fps.design/shots/family-sequence-of-sheets-morph-interaction) | Đọc trang/index; chưa phát recording. Giữ nguồn gốc khi panel đổi dạng. | Farm marker → inspector; WAAPI/FLIP, V | Motion lớn; mở tức thì | Chọn nguyên tắc |
| 2 | [60fps — Harvee graph morph](https://60fps.design/shots/harvee-tab-switch-graph-morph-interaction) | Mô tả indexed: đổi biểu diễn cùng dữ liệu. | Map/time/hash lens; shared selection, V | Mất ngữ cảnh; active event text | Chọn, không morph sai tọa độ dữ liệu |
| 3 | [60fps — Airbnb card carousel](https://60fps.design/shots/airbnb-yoga-class-card-carousel-morph-interaction) | Mô tả indexed; close trở lại nguồn. | Inspector return; FLIP, V | Không trả focus | Chọn nguyên tắc |
| 4 | [60fps — Family spinner minimize](https://60fps.design/shots/family-spinner-move-to-bottom-navigation-on-confirm-transaction) | Mô tả indexed; trạng thái pending có thể thu gọn. | API status island; CSS, T | Che kết quả request | Chọn tùy chỉnh, không trì hoãn API |
| 5 | [Design Spells — Interactive magnifier](https://designspells.com/spells/interactive-magnifier-in-preview) | Đọc mô tả; chưa xem recording. | Zoom vùng GPS/hash; clipped SVG, V | Pointer-only; nút detail thay thế | Chọn giới hạn một vùng |
| 6 | [Design Spells — Trip view](https://designspells.com/spells/trip-view-in-transit) | Đọc mô tả view chuyến đi. | Journey selection; SVG + native range, T | Drag-only; arrow/step buttons | Chọn |
| 7 | [Design Spells — Find My transitions](https://designspells.com/spells/animated-transitions-in-find-my) | Đọc mô tả; không tuyên bố đo easing. | Camera focus; transform SVG group, V | Zoom chóng mặt; static selection | Chọn |
| 8 | [microinteractions.dev — Hold confirm](https://microinteractions.dev/hold-confirm/) | Đọc code mẫu, cancel state. | Local tamper press feedback; CSS/WAAPI, T | Hold khó thao tác; click/keyboard equivalent | Tùy chọn, không bắt buộc giữ |
| 9 | [microinteractions.dev — Edge-aware tooltip](https://microinteractions.dev/edge-aware-tooltip/) | Đọc code mẫu positioning. | GPS/event hint; measured overlay, T | Tooltip ngoài viewport; focus mở detail | Chọn |
| 10 | [Codrops — SVG map animation](https://tympanus.net/codrops/2026/05/21/creating-scroll-driven-svg-map-animations-with-gsap/) | Đọc tutorial/code: camera groups, path drawing, progress point. | Route focus; SVG + WAAPI/rAF, V | Scroll pin/motion; không hijack scroll | Chọn nguyên tắc, không cài GSAP |
| 11 | [Motion Primitives — Morphing dialog](https://motion-primitives.com/docs/morphing-dialog) | Docs indexed; mở trực tiếp 403. | Shared inspector; local primitives trước, V | Focus/close origin | Chọn ý tưởng, chưa dùng thư viện |
| 12 | [Motion Primitives — Text morph](https://motion-primitives.com/docs/text-morph) | Docs indexed. | Stage label continuity; CSS crossfade, T | Animated text khó đọc | Chọn crossfade nhẹ, không hash scramble |
| 13 | [Magic UI — Animated theme toggler](https://magicui.design/docs/components/animated-theme-toggler) | Đọc docs mẫu radial View Transition. | Theme; native API, V | Snapshot nặng; feature/reduced-motion fallback | Chọn progressive enhancement |
| 14 | [Magic UI — Animated beam](https://magicui.design/docs/components/animated-beam) | Docs indexed; repeat mặc định cần sửa. | Verify/request flow; finite SVG dash, T | Vòng lặp gây hiểu lầm | Chọn chạy một lượt |
| 15 | [React Bits — Dock](https://reactbits.dev/components/dock) | Trang client không trích xuất code; catalog indexed. | Dock selection; CSS translate, T | Hover-only magnification | Chỉ chọn active indicator; chờ code |
| 16 | [Animata — Card spread](https://www.animata.design/docs/card/card-spread) | Đọc docs/code CSS. | Evidence stack preview; transform, T | Nội dung bị che/focus hidden | Dùng hạn chế cho preview |
| 17 | [Uiverse — Animated buttons](https://uiverse.io/ui/animated-buttons) | Đọc catalogue, chưa audit từng submission/license. | Primary action feedback; CSS, T | Glow/contrast/copy không kiểm chứng | Tham khảo; chưa chọn snippet |
| 18 | [Aceternity — Lens](https://ui.aceternity.com/components/lens) | Đọc docs component. | Contextual detail lens; clipped group, V | Touch/keyboard không hover | Chọn nguyên tắc, không cài kit |

Những package dùng Tailwind/shadcn chỉ là tài liệu tham khảo. Không thay stack CSS hiện tại để lấy một hiệu ứng. Các mục chỉ có index/description cần xem trực tiếp trước khi tái tạo choreography chi tiết.

## Ba hướng thiết kế, khác nhau từ cấu trúc

| | Atlas sống | Phòng bằng chứng | Nhật ký mùa vụ |
|---|---|---|---|
| Mood | Địa hình ấm, lạnh ở telemetry, chiều sâu vừa phải | Graphite, máy đo, tiêu điểm sáng trên bằng chứng | Editorial, giấy đất, typography biểu cảm |
| Layout/nav | Canvas không gian lớn, dock gọn, inspector nổi | Graph trung tâm, event rail, payload pane; palette | Bố cục spread bất đối xứng; mục lục bám ngữ cảnh |
| Density/type | Vừa; sans dễ đọc + mono tọa độ | Cao hơn; sans trung tính + mono có chọn lọc | Thấp; display lớn + side notes |
| Visualization | Địa điểm, tuyến, vùng nhiệt | Hash topology, JSON diff, authorization layers | Annotated journey và evidence archive |
| Motion | Camera focus, marker mở inspector, temporal scrub | Verify beam, seal, fracture và propagation | Chuyển vùng đọc, headline reveal, panel unfold |
| Strength | Hấp dẫn khi chạm, nối địa lý với dữ liệu | Điểm nhớ kỹ thuật rõ, nhiều thao tác có ý nghĩa | Nhận diện mạnh, typography gây ấn tượng |
| Risk | Dễ khiến sơ đồ giống dữ liệu GIS chính xác | Dễ thành terminal chật và quá nhiều nhãn nhỏ | Hiệu quả CRUD kém nếu mọi thao tác thành story |
| Desktop | Canvas rộng với inspector giữ ngữ cảnh | Evidence 2–3 vùng, tránh ép graph vào card | Spread hai cột và visualization lớn |
| Mobile | Map ngắn + sheet; timeline dưới ngón tay | Chuỗi block dọc, diff từng record | Một cột, headings rút gọn, controls rõ |

Chọn Atlas sống làm không gian sản phẩm, Phòng bằng chứng làm lớp kỹ thuật, lấy tỷ lệ chữ/khoảng thở từ Nhật ký mùa vụ. Không trộn ba bộ trang trí; cùng tokens, cùng selected event, cùng quy tắc timing.

## Dấu ấn đề xuất: đổi lớp nhìn, giữ nguyên đối tượng

Chọn event trên bản đồ → chuyển sang Journey → mở Integrity. Event đó vẫn được chọn, timestamp và event identity giữ vị trí dễ nhận biết. Biểu diễn đổi từ điểm địa lý sang điểm thời gian rồi thành block bằng chứng. Đây là **shared context**; chỉ những phần tử thực sự đại diện cùng dữ liệu mới dùng shared-element transition. Không uốn bản đồ thành đường nhiệt tùy tiện làm sai trục dữ liệu.

UI cần một selection model chung (`selectedEventId`, `selectedFarmId`, view lens) và các selector dữ liệu. Không thay API contract. Scrubber phải phản ứng trực tiếp với input; easing chỉ dành cho camera/panel phụ, không làm điểm dữ liệu chậm theo ngón tay. Nếu dữ liệu chỉ có bốn mốc, hiển thị bốn mốc; đường/nhiệt độ nội suy phải ghi rõ là nội suy mô phỏng.

## Inventory hiệu ứng được chọn

Chi phí triển khai tương đối: T/V/C = thấp/vừa/cao. Performance là dự kiến, phải đo trên browser. Mỗi dòng có trigger, ý nghĩa và fallback; không coi danh sách này là tất cả đều đã có.

| Hiệu ứng | Trigger → ý nghĩa / giá trị thông tin | Triển khai / performance | Tiếp cận và trạng thái |
|---|---|---|---|
| Đổi map/time/hash lens | Đổi view; theo cùng event qua ba biểu diễn | Shared state + FLIP/WAAPI; C/V | Focus heading/event, reduced-motion cập nhật tức thì; **đề xuất ưu tiên** |
| Camera bản đồ | Chọn stage/farm; đưa vị trí cần đọc vào tiêu điểm | Transform SVG group; V/V | Controls zoom/reset và list; không scroll hijack; đề xuất |
| Route beam | Chọn stage; chỉ phần tuyến liên quan | Stroke dash + point; T/T | Route tĩnh + stage labels; bản đơn giản đã có |
| Thermal ribbon | Scrub thời gian; xem vùng nhiệt tại mốc chọn | SVG segments, không blur canvas; V/T | Units + normal/warning/excursion text; đề xuất |
| GPS lock/crosshair | Chọn farm; xác nhận bản ghi và tọa độ | SVG/CSS one-shot; T/T | Button marker/list; ring tắt reduced-motion; bản đơn giản đã có |
| Marker → inspector | Mở farm; giữ nguồn gốc khi xem/chỉnh record | Một phép đo rồi FLIP, tránh đo mỗi frame; V/V | Trap focus chỉ khi modal; desktop pane không trap; đề xuất |
| UUID identity seal | Chọn farm; ổn định danh tính record | Typography + static SVG; T/T | UUID đầy đủ copy/đọc được; không gọi là chữ ký số; nền đã có |
| Timeline scrub | Range/step; đồng bộ route/GPS/temp/humidity/event | Native range + selected state; V/T | Arrow/step buttons; bản rời rạc đã có, cần nối toàn cục |
| Verification beam | Replay; nối payload → previous hash → digest → seal | Web Crypto + finite SVG; V/T | Hash thực và kết luận text; tính hash/replay đã có, choreography nâng cấp |
| Hash diff | Tamper; thấy field đổi và digest thực đổi | Highlight ký tự khác sau tính xong; V/T | JSON before/after text; source diff có, hex diff đề xuất |
| Link fracture | Tamper event; phân biệt mismatch tại nguồn và ancestry sau đó | Từng connector + một propagation; V/T | Mismatch/ancestry labels; bản đơn giản đã có |
| Tenant membranes | Chạy GET; giúp hiểu tenant nào nhận được records | Diagram fixture + actual fetch outcome; V/T | Caption kiến trúc suy ra, table kết quả; đề xuất |
| Request status island | Request bắt đầu/kết thúc; phản hồi network nhỏ gọn | State theo promise + CSS; T/T | aria-live summary, không delay API; đề xuất |
| Radial theme reveal | Theme button; đổi chất liệu không gian | View Transition nếu hỗ trợ; V/V | Feature detection + reduced motion switch ngay; đề xuất |
| Contextual lens | Inspect GPS/payload; phóng chi tiết tại chỗ | Clip một vùng SVG; V/V | Click/focus detail pane, tắt hover lens trên touch; đề xuất sau |
| Dock indicator | Chọn destination; hướng nhìn di chuyển theo ngữ cảnh | Translate/opacity; T/T | Labeled buttons, active state; dock có, indicator nâng cấp |
| Odometer ngắn | Value đổi bởi scrub; nhấn biến đổi số có thật | Tabular fixed-width digits; V/T | Text số thật, reduced-motion trực tiếp; cân nhắc sau |
| Primary press/magnet nhỏ | Pointer fine trên một primary action; cảm giác phản hồi | Transform giới hạn 4px, cleanup RAF; V/T | Không di chuyển hit area; bỏ coarse/reduced motion; thử sau |
| Kinetic heading một lần | Vào view; nhấn trọng tâm thị giác | Translate/opacity; T/T | DOM text liền mạch, không letter spam; tùy chọn |
| Hold feedback tùy chọn | Press local tamper; thể hiện chủ động tác động nguồn | CSS progress + cancel; V/T | Click/keyboard tương đương, Undo; không bắt buộc hold |

Không chọn full-screen particle, cursor takeover, nền 3D chạy liên tục, hash giả đảo ký tự, radar tự quay khi dữ liệu không live, lỗi rung vô hạn hay animation bảng lớn. Mặt nền có thể có grain tĩnh rất nhẹ; chiều sâu chính đến từ composition và tương phản.

## Hệ thống motion và chất liệu

- 120–180ms cho press/focus; 180–320ms cho selection; 300–550ms cho inspector/shared context; 800–1800ms cho replay do người dùng kích hoạt. Không áp delay vào API.
- Direct manipulation không easing dữ liệu theo sau; camera có thể ease-out ngắn. Animation bị ngắt phải đi đến trạng thái mới hợp lệ, không khóa controls.
- Light: giấy đất/off-white, graphite, crop green có giới hạn, frost cho nhiệt độ. Dark: graphite rộng, bằng chứng nổi sáng, amber cảnh báo, đỏ chỉ failure. Dark không cần giống cyberpunk.
- Mỗi view có một vùng thị giác chủ đạo. Diện tích chính dành cho map/trace/evidence; thông tin phụ có thể là rail hoặc chữ trên canvas thay vì card đồng kích thước.
- Sửa typography trước khi thêm hiệu ứng: body 14–16px; labels quan trọng 11–12px trở lên; heading fluid khoảng 36–88px. Lượt hoàn thiện đã nâng nhãn dữ liệu lên tối thiểu 11px; không giảm font để vừa layout.
- [Be Vietnam Pro metadata](https://github.com/google/fonts/blob/main/ofl/bevietnampro/METADATA.pb) và [IBM Plex Mono metadata](https://github.com/google/fonts/blob/main/ofl/ibmplexmono/METADATA.pb) chính thức có subset Vietnamese và license OFL, đã đọc qua GitHub connector. Đề xuất phục vụ font local, kèm license; chưa thêm font asset vào repo. Kiểm tra font thực, shaping dấu và fallback khi triển khai.

## Vướng mắc: đâu là giới hạn thật?

| Quan sát từ repo/môi trường | Tác động | Cách xử lý / điều chưa thể khẳng định |
|---|---|---|
| Backend hiện có auth/farms, items placeholder; chưa có API shipment/sensor/event | Digital twin không thể tự biến thành telemetry live | Fixture local có nhãn rõ; vẫn làm đẹp đầy đủ. Tích hợp live cần API/data bổ sung ở scope sau |
| Farm chỉ có UUID, tenant, name, area, lat/lon | Không biết biên thửa/đường xe chạy | Plot tọa độ thật; glyph diện tích đại diện, không vẽ polygon giả như ranh đất thật |
| CSP connect-src chỉ self/backend; font-src self/data | Tile API/font CDN không dùng trực tiếp theo cấu hình hiện tại | Basemap SVG/GeoJSON đơn giản và font local; không nới CSP chỉ để animation |
| Permissions-Policy chặn geolocation | Không lấy vị trí browser người dùng | Dùng GPS trong record; không gọi tọa độ fixture là GPS live |
| API không xuất per-layer spans | Không đo được thời gian RBAC/Tenant/RLS từ frontend | Actual request pending/status/rows; diagram nội bộ là mô hình suy từ code, không packet tracing thật |
| Web Crypto cần secure context | Hash có thể không chạy trên HTTP LAN tùy deployment | HTTPS production/localhost dev; thông báo lỗi thật, không hash placeholder |
| Browser local bị chặn | Không chạy Chromium trong workspace | Đã chạy browser thật trên GitHub Actions: desktop/tablet/mobile, hai theme, native reduced motion; có ảnh chụp |
| Không có PostgreSQL local | Cần môi trường test độc lập | Đã chạy FastAPI + PostgreSQL 16 trong CI, kiểm thử login thật/demo/roles/persistence/isolation; credential ngẫu nhiên không log/upload |

Nguồn kiểm tra: `frontend/nginx.conf`, `render.yaml`, `backend/app/api/v1/router.py`, `backend/app/api/v1/endpoints/farms.py`, `backend/app/schemas/farm.py`, `backend/app/core/authorization.py`, `backend/app/core/tenancy.py`, `frontend/src/services`, `frontend/src/domain/demoScenario.ts`.

Natural Earth cung cấp dữ liệu bản đồ public domain ([terms](https://www.naturalearthdata.com/about/terms-of-use/)). Đây là một candidate basemap local, **không** phải dữ liệu ranh thửa. Khi nhập dữ liệu phải chọn projection, simplify geometry và ghi nguồn; chưa thêm asset bản đồ ở lượt này.

## Kiến trúc chuyển động và hiệu năng

CSS → SVG/CSS → WAAPI/View Transitions/FLIP. Chỉ cân nhắc Motion for React nếu chuyển tiếp nhiều inspector/cross-view làm cleanup và interrupt handling phức tạp đáng kể; phải so bundle và độ rõ code trước. Không có lý do hiện tại để thêm Three.js, GSAP, Tailwind hoặc shadcn.

Shared state giữ domain selection, không lưu frame animation trong React state mỗi frame. Compute hash khi payload đổi, không mỗi tick. RAF chỉ chạy khi có input/playback, hủy khi unmount/hidden; IntersectionObserver dùng cho visualization có playback. Đọc bounding box một lần trước animation, không xen kẽ read/write mỗi frame. Ưu tiên transform/opacity; SVG dash/clip là paint có giới hạn vùng, cần profile. View Transition có snapshot nên không mặc định bật mọi view trên mobile.

Mục tiêu 60fps không phải lời bảo đảm. Đo frame time, long task, layout shift trên máy thật; một frame ở 60Hz có khoảng 16.7ms tổng ngân sách. Nếu lens/camera tốn chi phí, giảm choreography chứ giữ nguyên dữ liệu. Native focus, semantic DOM, touch targets khoảng 44px và reduced-motion state đầy đủ là phần của design, không phải polish cuối.

Nguồn kỹ thuật: [web.dev animation guide](https://web.dev/articles/animations-guide), [MDN startViewTransition](https://developer.mozilla.org/en-US/docs/Web/API/Document/startViewTransition), [WAI modal dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), [MDN reduced motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion).

## Trình tự triển khai được dùng

1. Typography, tỷ lệ canvas, palette light/dark và layout mobile; đưa labels về kích thước đọc được. Giữ tour là phụ.
2. Nối selected event toàn cục; tạo một lát cắt hoàn chỉnh map → time → evidence. Kiểm tra focus/interrupt/reduced-motion trước mở rộng.
3. Nâng Farm Atlas thành canvas có camera + marker inspector, giữ nguyên create/edit/services và UUID.
4. Nâng hash replay/diff/fracture; thử ba trạng thái độc lập: bình thường, excursion nhưng hash hợp lệ, tamper làm mismatch/ancestry invalid.
5. Security request visual gắn real status, caption mô hình kiến trúc; theme reveal/lens chỉ thêm sau khi các vùng chính ổn.
6. Khi browser/backend sẵn sàng: build/lint; screenshots desktop/tablet/mobile light/dark; keyboard/200% zoom/reduced motion; login/demo, Grower/Admin/Inspector, allowed/403, create/edit/RLS bằng dữ liệu test. Browser automation và backend CI đã chạy; screen reader thủ công, 200% zoom và profiling máy thật vẫn chưa được xác nhận.

Tiêu chí thành công: người dùng tự muốn thử thêm một tương tác vì nó đẹp và giải thích được dữ liệu; CRUD/auth vẫn dùng ngay được; toàn bộ sản phẩm có một ngôn ngữ thị giác chung. Không cần diễn thuyết để hiểu sức hút đó.
