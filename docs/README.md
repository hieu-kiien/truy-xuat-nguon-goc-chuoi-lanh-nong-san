# Tài liệu dự án

Ưu tiên đọc:
1. [Hướng dẫn chạy](../README.md)
2. [Quy tắc nhóm — Definition of Done và Definition of Ready](DOD-DOR.md)
3. [Cách dùng Jira của nhóm và vai trò thành viên](JIRA-GUIDE.md)
4. [Nghiệm thu Sprint 1–4 và quyết định thiết kế](ACCEPTANCE.md)
5. [API](api.md), [quyền DB](database.md), [chuỗi hash](N3-4-INTEGRITY.md), [báo cáo PDF](N3-72-PDF.md)
6. [Mẫu phả hệ và oracle](LINEAGE-ACCEPTANCE.md)
7. [Quyết định xoá dữ liệu định danh (R-06)](N3-141-RISK-R06.md)
8. [Sao lưu cơ sở dữ liệu và khôi phục](BACKUP-RECOVERY.md)
9. [Biên bản diễn tập khôi phục](RESTORE-DRILLS.md)
10. [Vận hành hệ thống](OPERATIONS.md)
11. [Rà soát rủi ro dự án](RISK-REVIEW.md)

Không xóa migrations hoặc oracle để giảm số file: chúng vẫn cần cho nâng cấp DB và kiểm chứng.

Báo cáo/coverage/CSV sinh tự động có thể tái tạo, để trong artifact CI hoặc `local_docs/` đã được gitignore. Không commit node_modules, .venv, cache, bản build hoặc dữ liệu trình diễn.
