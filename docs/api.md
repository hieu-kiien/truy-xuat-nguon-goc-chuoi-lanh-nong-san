# Tài liệu API — TTCS N3

Tài liệu này mô tả các API endpoint của Backend.  
Mọi thành viên frontend đều có thể đọc file này để biết cách gọi API.

> 💡 **Tip:** Sau khi backend chạy, truy cập http://localhost:8000/docs để xem tài liệu API tương tác (do FastAPI tự sinh).

---

## Base URL

| Môi trường | URL |
|---|---|
| Development | `http://localhost:8000/api/v1` |

---

## Endpoints

### Health Check
```
GET /
```
**Response:**
```json
{ "status": "ok", "message": "TTCS Backend đang chạy ✅" }
```

---

### Items (Ví dụ minh họa)

#### Lấy tất cả items
```
GET /api/v1/items/
```

#### Lấy item theo ID
```
GET /api/v1/items/{item_id}
```

---

*Thêm endpoint mới vào đây khi team xây dựng thêm tính năng.*
