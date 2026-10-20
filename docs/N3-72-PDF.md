# N3-72 — Xuất hồ sơ truy xuất PDF kèm kết quả kiểm toàn vẹn

## Phạm vi
Từ trang chi tiết lô, người dùng có quyền xem lô tải được một tệp PDF A4 chứa toàn bộ hồ sơ truy xuất của lô. Hồ sơ được sinh lại từ dữ liệu hiện hành mỗi lần tải, không lưu tệp trên máy chủ.

## Nội dung hồ sơ
1. **Thông tin lô:** mã lô, tên lô, sản phẩm, ngày thu hoạch, khối lượng ban đầu/còn lại, trạng thái, đơn vị đang giữ, đơn vị sở hữu, vùng trồng, địa điểm hiện tại, UUID.
2. **Kết quả kiểm tra toàn vẹn:** trạng thái hợp lệ/sai lệch, số sự kiện đã kiểm, sự kiện sai lệch đầu tiên, danh sách lỗi theo từng sự kiện, thời điểm kiểm tra (GMT+7).
3. **Lịch sử sự kiện đầy đủ:** số thứ tự, thời điểm ghi nhận, loại sự kiện, đơn vị ghi nhận, nội dung payload rút gọn, 12 ký tự đầu của mã băm và trạng thái xác minh từng sự kiện (Hợp lệ / Sai lệch / Chưa xác minh).
4. **Thông tin đối chiếu:** mã băm sự kiện cuối cùng để so với API kiểm tra toàn vẹn.

## Quy tắc nghiệp vụ
- Quyền: `lots:read`; phạm vi dữ liệu theo tổ chức như các API đọc khác. Sự kiện của bên thứ ba hoặc tham chiếu ngoài phạm vi bị ẩn payload và ghi rõ trong hồ sơ.
- Kiểm tra toàn vẹn dùng lại `verify_event_chain` của N3-4, tính trên chuỗi chuẩn (chưa ẩn payload) để kết quả không phụ thuộc quyền xem.
- Endpoint `GET /api/v1/lots/{lot_id}/report.pdf` chỉ đọc: không tạo bản ghi `integrity_checks`, trả `Cache-Control: no-store`.
- Tên tệp chỉ giữ ký tự `[A-Za-z0-9_-]` để an toàn cho header HTTP.

## Giới hạn
Hash chain phát hiện dữ liệu bị sửa/thiếu so với chuỗi đã ghi trong cùng cơ sở dữ liệu. Hồ sơ không phải chữ ký số và không thay thế kết luận giám định hay giá trị chứng cứ pháp lý (xem thêm `docs/N3-4-INTEGRITY.md`).

## Kiểm thử
- Backend: `backend/tests/test_lot_report.py` — nội dung PDF (trích xuất văn bản), trường hợp chuỗi hợp lệ, chuỗi bị sửa, 403 với tổ chức khác, tên tệp an toàn.
- Frontend: `frontend/tests/n3-72-lot-pdf-report.test.mjs` — nút tải hồ sơ, endpoint được gọi, tên tệp, hiển thị lỗi.
