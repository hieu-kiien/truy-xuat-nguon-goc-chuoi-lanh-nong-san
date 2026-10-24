# Tài liệu Kỹ thuật & Nghiệm thu Dự án

Thư mục này tập hợp đầy đủ hồ sơ thiết kế, đặc tả kỹ thuật, quy trình vận hành và biên bản nghiệm thu của hệ thống **VietFarm Trace (AgroChain)** qua 8 Sprint (`N3-1` → `N3-160`).

## Thứ tự đọc khuyến nghị

1. [Hướng dẫn cài đặt, chạy dự án & tài khoản Demo](../README.md)
2. [Định hướng sản phẩm & phạm vi hệ thống](../PRODUCT.md)
3. [Quy tắc nhóm — Definition of Done và Definition of Ready](DOD-DOR.md)
4. [Cách dùng Jira của nhóm và vai trò thành viên](JIRA-GUIDE.md)
5. [Báo cáo nghiệm thu tổng hợp (Sprint 1 – Sprint 8)](ACCEPTANCE.md)
6. [Đặc tả API (OpenAPI / REST)](api.md) · [Kiến trúc CSDL & phân quyền RLS](database.md)
7. [Cơ chế chuỗi băm SHA-256 / RFC 8785 (N3-4)](N3-4-INTEGRITY.md) · [Xuất báo cáo PDF A4 (N3-72)](N3-72-PDF.md)
8. [Mẫu đồ thị phả hệ và bộ đáp án kiểm chứng (Oracle)](LINEAGE-ACCEPTANCE.md)
9. [Quyết định kiến trúc xóa/ẩn danh dữ liệu định danh PII (R-06 / N3-141)](N3-141-RISK-R06.md)
10. [Quy trình sao lưu cơ sở dữ liệu và khôi phục (N3-76)](BACKUP-RECOVERY.md) · [Biên bản diễn tập khôi phục thực tế](RESTORE-DRILLS.md)
11. [Vận hành hệ thống, job bảo trì và hạ tầng Staging (R-10 / N3-145 / N3-160)](OPERATIONS.md)
12. [Hồ sơ rà soát và đóng rủi ro dự án (Sprint 8)](RISK-REVIEW.md)

---

## Nguyên tắc bảo toàn hồ sơ kiểm chứng

- Giữ nguyên toàn bộ chuỗi tệp nâng cấp cơ sở dữ liệu (`backend/alembic/versions/`) và các bộ đáp án kiểm thử phả hệ (`backend/tests/data/*-oracle.json`) để đảm bảo khả năng tái lập môi trường và kiểm chứng tự động bất kỳ lúc nào.
- Các bản lưu trữ lịch sử nghiệm thu từng giai đoạn được bảo lưu tại [`docs/acceptance/`](acceptance/README.md).
