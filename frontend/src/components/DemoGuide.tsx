import { useState } from 'react'
import { TaskLink } from './TaskLink'

const steps = [
  {title: 'Chuẩn bị danh mục', role: 'Quản trị hệ thống (admin@system.vn)', href: '/products', action: 'Thêm hoặc sửa một nông sản mẫu (đã có sẵn Dâu tây Cầu Đất, Rau thủy canh Đà Lạt, Chè Shan Tuyết Mộc Châu, Bắp cải xanh). Có thể nhập CSV theo tệp mẫu.', check: 'Sản phẩm xuất hiện trong danh mục; CSV sai chỉ rõ dòng/cột và không lưu một phần.'},
  {title: 'Khai báo vùng trồng', role: 'Nông trại / HTX (grower@caudat.vn hoặc admin@mocchau.vn)', href: '/farms', action: 'Thêm vùng trồng mới hoặc mở sửa vùng trồng mẫu (Khu Nhà Kính Công Nghệ Cao A1, Đồi Chè Trái Tim Tiểu Khu 68) để cập nhật tên.', check: 'Vùng trồng được lưu trong đúng đơn vị và có thể chọn khi tạo lô.'},
  {title: 'Tạo lô thu hoạch', role: 'Nông trại / HTX (grower@caudat.vn)', href: '/lots?task=create', action: 'Chọn vùng trồng và nông sản, tạo lô 40 kg (hoặc dùng sẵn "Dâu tây Cầu Đất — Lô nông trại 40kg").', check: 'Có mã lô mới, còn 40 kg và sự kiện thu hoạch trong Lịch sử sự kiện.'},
  {title: 'Ghi nhận hoạt động', role: 'Đơn vị đang giữ lô (grower@caudat.vn)', href: '/lots', action: 'Mở lô "Dâu tây Cầu Đất — Lô nông trại 40kg" → Ghi nhận hoạt động. Chọn kho lạnh, ghi nhiệt độ đo được và xác nhận lưu.', check: 'Sự kiện xuất hiện trong lịch sử. Không có thao tác sửa/xóa sự kiện.'},
  {title: 'Bàn giao và xác nhận', role: 'Bên gửi (grower@caudat.vn) rồi bên nhận (admin@mocchau.vn)', href: '/handovers', action: 'Gửi lô sang HTX Mộc Châu. Đăng xuất, đăng nhập bên nhận (admin@mocchau.vn) → Xử lý yêu cầu → Xác nhận nhận lô. Dùng yêu cầu khác để thử từ chối có lý do.', check: 'Khi chờ, lô chưa đổi chủ giữ. Sau xác nhận, bên nhận được thao tác; bên gửi chỉ còn lịch sử cho phép.'},
  {title: 'Tách lô', role: 'HTX / đơn vị phân phối đang giữ (admin@mocchau.vn)', href: '/lots', action: 'Mở lô "Dâu tây Cầu Đất — Lô HTX 40kg (Sẵn sàng tách lô)" → Tách lô → nhập hai lô con 10 và 20 kg. Thử nhập tổng trên 40 kg trước khi lưu.', check: 'Nút lưu bị khóa khi vượt lượng. Khi thành công, có hai mã con và lô nguồn còn 10 kg.'},
  {title: 'Gộp lô', role: 'HTX / đơn vị phân phối đang giữ (admin@mocchau.vn)', href: '/lots', action: 'Chọn sản phẩm Dâu tây Cầu Đất, tích chọn hai lô "Lô thành phần A" (20 kg) và "Lô thành phần B" (25 kg) → Gộp lô đã chọn.', check: 'Tổng cập nhật trực tiếp; lô khác sản phẩm không chọn được. Lô mới giữ quan hệ với cả hai nguồn.'},
  {title: 'Truy xuất nguồn gốc', role: 'Tài khoản có quyền xem lô (distributor@phanphoi.vn hoặc admin@mocchau.vn)', href: '/lots', action: 'Chọn sản phẩm Bắp cải xanh, mở lô gộp M1/M2/M3 hoặc lô đầu ra D1..D6 → Nguồn gốc. Phóng to/thu nhỏ và thu gọn/mở nhánh; bấm mã lô để xem nguồn.', check: 'Thấy các nguồn, vùng trồng và khối lượng liên kết; đọc được cả danh sách lô liên quan.'},
  {title: 'Địa điểm và di chuyển', role: 'Đơn vị phân phối (distributor@phanphoi.vn)', href: '/lots?task=locations', action: 'Kiểm tra hai địa điểm mẫu (Kho lạnh Trung tâm Quận 7, Cửa hàng Rau sạch Quận 1) hoặc thêm mới. Mở lô "Bắp cải xanh — D1" → Di chuyển lô và chọn địa điểm nhận.', check: 'Địa điểm hiện tại đổi và có sự kiện di chuyển. Không dùng địa điểm của đơn vị khác.'},
  {title: 'Ghi nhận tiêu thụ', role: 'Đơn vị phân phối đang giữ (distributor@phanphoi.vn)', href: '/lots', action: 'Mở lô "Bắp cải xanh — D1" (40 kg đang hoạt động) → Ghi nhận tiêu thụ → đọc cảnh báo, tích xác nhận và lưu (hoặc đối chiếu lô "Bắp cải xanh — D2" đã tiêu thụ mẫu).', check: 'Lượng còn lại về 0, trạng thái Đã tiêu thụ; các thao tác tiếp theo không khả dụng.'},
  {title: 'Kiểm tra toàn vẹn và nhật ký', role: 'Quản trị / kiểm định (inspector@chicuc.gov.vn); nhật ký chỉ quản trị hệ thống (admin@system.vn)', href: '/integrity', action: 'Kiểm tra chuỗi sự kiện của lô vừa thao tác. Đăng nhập admin@system.vn mở Phân quyền để xem Nhật ký thao tác.', check: 'Có kết quả kiểm tra, thời gian và số sự kiện. Nhật ký ghi người thao tác, đối tượng và kết quả.'},
  {title: 'Bàn giao quá hạn và quyền xem', role: 'Bên gửi (grower@caudat.vn), bên nhận (admin@mocchau.vn) và tài khoản đơn vị khác (distributor@phanphoi.vn)', href: '/handovers', action: 'Dùng yêu cầu demo "Dâu tây Cầu Đất — Lô chờ xác nhận (Quá hạn 48h)" đã được gắn cờ quá hạn; xem ở hai phía rồi xác nhận muộn. Đổi tài khoản để kiểm tra lô ngoài quyền.', check: 'Có nhãn Quá hạn nhưng vẫn nhận được lô; tài khoản ngoài quyền không xem/thao tác được lô.'},
]

export function DemoGuide() {
  const [selected, setSelected] = useState(0)
  const [done, setDone] = useState<Set<number>>(new Set())
  const step = steps[selected]
  return <div className="info-stack">
    <section className="panel-card panel-box">
      <h2>Trình diễn từng tính năng</h2>
      <p>Bộ mẫu Bắp cải xanh có 18 lô: 3 lô thu hoạch (R1..R3) → 6 lô tách (R1A..R3B) → 3 lô gộp chéo (M1..M3) → 6 lô tách cuối (D1..D6). Chọn Bắp cải xanh trong danh sách lô để đối chiếu nguồn từ hai thửa khác nhau.</p>
      <p>Hệ thống đã khởi tạo sẵn toàn bộ 5 tài khoản mẫu (mật khẩu <code>Password123!</code>) cùng các lô Dâu tây Cầu Đất ở từng trạng thái (sẵn sàng ghi sự kiện, tách lô, gộp lô, bàn giao quá hạn 48h) để trình diễn ngay từng bước mà không cần tạo lại dữ liệu thủ công.</p>
      <p className="panel-sub">Các trang dùng chung phiên đăng nhập. Khi đổi vai trò, đăng xuất rồi chọn nhanh tài khoản bên tiếp theo ngay trên màn hình đăng nhập.</p>
      <label className="form-field">Chọn bước trình diễn<select value={selected} onChange={event => setSelected(Number(event.target.value))}>{steps.map((item, index) => <option key={item.title} value={index}>{index + 1}. {item.title}{done.has(index) ? ' ✓' : ''}</option>)}</select></label>
    </section>
    <section className="panel-card panel-box">
      <h2>{selected + 1}. {step.title}</h2>
      <p><strong>Tài khoản thực hiện:</strong> {step.role}</p>
      <p><strong>Cách thao tác:</strong> {step.action}</p>
      <p><strong>Kết quả cần đối chiếu:</strong> {step.check}</p>
      <div className="action-row"><TaskLink href={step.href}>Mở màn hình thao tác</TaskLink><button type="button" className="ds-button ds-button-secondary" disabled={selected === 0} onClick={() => setSelected(value => value - 1)}>Bước trước</button><button type="button" className="ds-button ds-button-secondary" disabled={selected === steps.length - 1} onClick={() => setSelected(value => value + 1)}>Bước tiếp</button></div>
      <label className="demo-check"><input type="checkbox" checked={done.has(selected)} onChange={event => setDone(current => {const next = new Set(current); if (event.target.checked) next.add(selected); else next.delete(selected); return next})} /> Tôi đã thao tác và đối chiếu kết quả của bước này.</label>
      <p className="panel-sub">Đã tự đối chiếu {done.size}/{steps.length} bước trong lần mở hướng dẫn này. Đây là checklist trình diễn, không tự động xác nhận nghiệm thu.</p>
    </section>
  </div>
}
