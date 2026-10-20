# Tài liệu dự án

Ưu tiên đọc:
1. [Hướng dẫn chạy](../README.md)
2. [Nghiệm thu Sprint 1–4 và quyết định thiết kế](ACCEPTANCE.md)
3. [API](api.md), [quyền DB](database.md), [chuỗi hash](N3-4-INTEGRITY.md), [báo cáo PDF](N3-72-PDF.md)
4. [Mẫu phả hệ và oracle](LINEAGE-ACCEPTANCE.md)
5. [Quyết định xoá dữ liệu định danh (R-06)](N3-141-RISK-R06.md)

Không xóa migrations hoặc oracle để giảm số file: chúng vẫn cần cho nâng cấp DB và kiểm chứng.

Báo cáo/coverage/CSV sinh tự động có thể tái tạo, để trong artifact CI hoặc `local_docs/` đã được gitignore. Không commit node_modules, .venv, cache, bản build hoặc dữ liệu trình diễn.
