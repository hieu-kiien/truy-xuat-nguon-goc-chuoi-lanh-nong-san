# Ảnh bàn giao AgroChain

14 PNG chụp trực tiếp bằng Chromium từ **production entry** cùng FastAPI/PostgreSQL thật trong database CI dùng một lần. Không chỉnh sửa ảnh, không tạo hình bằng AI, không dùng preview transport giả.

Nguồn: [Visual QA run 37001594645](https://github.com/hieu-kiien/truy-xuat-nguon-goc-chuoi-lanh-nong-san/actions/runs/37001594645), commit `3d9f9a0b346e852764d84a9c96c422f2752f3d55`; artifact `agrochain-live-browser-qa`. Test data bao gồm các record Browser QA tạo ở bài CRUD trước đó.

`desktop-*`: viewport 1440×1000. `mobile-*`: viewport 390×844. Ảnh full-page giữ thanh điều hướng fixed ở vị trí viewport khi chụp; đây là ảnh toàn tài liệu, không phải một màn hình điện thoại cao như toàn ảnh. Animation được tạm dừng bằng Playwright để capture ổn định, ứng dụng vẫn có motion khi tương tác.

| Màn hình | Desktop | Mobile |
|---|---|---|
| Secure Gateway | [desktop-gateway.png](desktop-gateway.png) | [mobile-gateway.png](mobile-gateway.png) |
| Trace Command Center | [desktop-trace.png](desktop-trace.png) | [mobile-trace.png](mobile-trace.png) |
| Farm Atlas | [desktop-atlas.png](desktop-atlas.png) | [mobile-atlas.png](mobile-atlas.png) |
| Cold Chain Journey | [desktop-journey.png](desktop-journey.png) | [mobile-journey.png](mobile-journey.png) |
| Integrity Lab | [desktop-forensics.png](desktop-forensics.png) | [mobile-forensics.png](mobile-forensics.png) |
| Security X-Ray | [desktop-security.png](desktop-security.png) | [mobile-security.png](mobile-security.png) |
| Field Guide | [desktop-field-guide.png](desktop-field-guide.png) | [mobile-field-guide.png](mobile-field-guide.png) |

Light/dark, tablet, 320px, native reduced-motion và các trạng thái chi tiết nằm ở artifact `agrochain-visual-qa` của cùng run. CI artifact giữ 14 ngày; PNG trong thư mục này là bộ bàn giao lâu dài. Research/design system/inventory/a11y/performance và kết quả test nằm ở các tài liệu cấp frontend.
