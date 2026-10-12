import { useState } from 'react'
import { TaskLink } from './TaskLink'

const steps = [
  {title: 'Chuẩn bị danh mục', role: 'Quản trị hệ thống', href: '/products', action: 'Thêm hoặc sửa một nông sản mẫu. Có thể nhập CSV theo tệp mẫu.', check: 'Sản phẩm xuất hiện trong danh mục; CSV sai chỉ rõ dòng/cột và không lưu một phần.'},
  {title: 'Khai báo vùng trồng', role: 'Nông trại / HTX', href: '/farms', action: 'Thêm vùng trồng, nhập diện tích và tọa độ. Mở sửa để cập nhật tên.', check: 'Vùng trồng được lưu trong đúng đơn vị và có thể chọn khi tạo lô.'},
  {title: 'Tạo lô thu hoạch', role: 'Nông trại / HTX', href: '/lots?task=create', action: 'Chọn vùng trồng và nông sản, tạo lô 40 kg.', check: 'Có mã lô mới, còn 40 kg và sự kiện thu hoạch trong Lịch sử sự kiện.'},
  {title: 'Ghi nhận hoạt động', role: 'Đơn vị đang giữ lô', href: '/lots', action: 'Mở lô → Ghi nhận hoạt động. Chọn kho lạnh, ghi nhiệt độ đo được và xác nhận lưu.', check: 'Sự kiện xuất hiện trong lịch sử. Không có thao tác sửa/xóa sự kiện.'},
  {title: 'Bàn giao và xác nhận', role: 'Bên gửi rồi bên nhận', href: '/handovers', action: 'Gửi lô sang HTX. Đăng xuất, đăng nhập bên nhận → Xử lý yêu cầu → Xác nhận nhận lô. Dùng yêu cầu khác để thử từ chối có lý do.', check: 'Khi chờ, lô chưa đổi chủ giữ. Sau xác nhận, bên nhận được thao tác; bên gửi chỉ còn lịch sử cho phép.'},
  {title: 'Tách lô', role: 'HTX / đơn vị phân phối đang giữ', href: '/lots', action: 'Mở lô 40 kg → Tách lô → nhập hai lô con 10 và 20 kg. Thử nhập tổng trên 40 kg trước khi lưu.', check: 'Nút lưu bị khóa khi vượt lượng. Khi thành công, có hai mã con và lô nguồn còn 10 kg.'},
  {title: 'Gộp lô', role: 'HTX / đơn vị phân phối đang giữ', href: '/lots', action: 'Tích chọn hai lô con cùng nông sản → Gộp lô đã chọn. Giữ mặc định lấy hết lượng hoặc điều chỉnh từng phần.', check: 'Tổng cập nhật trực tiếp; lô khác sản phẩm không chọn được. Lô mới giữ quan hệ với cả hai nguồn.'},
  {title: 'Truy xuất nguồn gốc', role: 'Tài khoản có quyền xem lô', href: '/lots', action: 'Mở lô gộp → Nguồn gốc. Phóng to/thu nhỏ và thu gọn/mở nhánh; bấm mã lô để xem nguồn.', check: 'Thấy các nguồn, vùng trồng và khối lượng liên kết; đọc được cả danh sách lô liên quan.'},
  {title: 'Địa điểm và di chuyển', role: 'Đơn vị phân phối', href: '/lots?task=locations', action: 'Thêm hai cửa hàng/kho của đơn vị. Nhận lô rồi mở Di chuyển lô và chọn địa điểm nhận.', check: 'Địa điểm hiện tại đổi và có sự kiện di chuyển. Không dùng địa điểm của đơn vị khác.'},
  {title: 'Ghi nhận tiêu thụ', role: 'Đơn vị phân phối đang giữ', href: '/lots', action: 'Dùng một lô demo riêng → Ghi nhận tiêu thụ → đọc cảnh báo, tích xác nhận và lưu.', check: 'Lượng còn lại về 0, trạng thái Đã tiêu thụ; các thao tác tiếp theo không khả dụng.'},
  {title: 'Kiểm tra toàn vẹn và nhật ký', role: 'Quản trị / kiểm định; nhật ký chỉ quản trị hệ thống', href: '/integrity', action: 'Kiểm tra chuỗi sự kiện của lô vừa thao tác. Quản trị mở Phân quyền để xem Nhật ký thao tác.', check: 'Có kết quả kiểm tra, thời gian và số sự kiện. Nhật ký ghi người thao tác, đối tượng và kết quả.'},
  {title: 'Bàn giao quá hạn và quyền xem', role: 'Bên gửi, bên nhận và tài khoản đơn vị khác', href: '/handovers', action: 'Dùng yêu cầu demo đã quá hạn 48 giờ sau lần quét bảo trì; xem ở hai phía rồi xác nhận muộn. Đổi tài khoản để kiểm tra lô ngoài quyền.', check: 'Có nhãn Quá hạn nhưng vẫn nhận được lô; tài khoản ngoài quyền không xem/thao tác được lô.'},
]

export function DemoGuide() {
  const [selected, setSelected] = useState(0)
  const [done, setDone] = useState<Set<number>>(new Set())
  const step = steps[selected]
  return <div className="info-stack">
    <section className="panel-card panel-box">
      <h2>Trình diễn từng tính năng</h2>
      <p>Bộ mẫu Bắp cải xanh có 18 lô: 3 lô thu hoạch → 6 lô tách → 3 lô gộp chéo → 6 lô tách cuối. Chọn Bắp cải xanh trong danh sách lô để đối chiếu nguồn từ hai thửa khác nhau.</p>
      <p>Dùng dữ liệu demo và ghi lại mã lô vừa tạo. Mỗi tài khoản chỉ thấy các thao tác đúng quyền và trạng thái lô.</p>
      <p className="panel-sub">Các trang dùng chung phiên đăng nhập. Khi đổi vai trò, đăng xuất rồi đăng nhập tài khoản bên tiếp theo và tải lại các tab còn mở.</p>
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
