# Tài liệu đặc tả API

Tài liệu kỹ thuật mô tả các RESTful API của hệ thống. Để thử nghiệm trực tiếp các endpoint, truy cập giao diện Swagger UI tại `/docs` khi máy chủ Backend đang hoạt động.

## Base URL

| Môi trường | Địa chỉ |
|---|---|
| Local | `http://localhost:8000` |
| Staging | `https://ttcs-backend-staging.onrender.com` |

---

## Endpoints

### 1. Health Check
Kiểm tra trạng thái hoạt động của dịch vụ Backend.

- **Method:** `GET`
- **Path:** `/`
- **Response `200 OK`:**
```json
{
  "status": "ok",
  "message": "Backend service is online"
}
```

### 2. Items
Ví dụ mẫu cho định tuyến API phiên bản v1.

- **Lấy danh sách:** `GET /api/v1/items/`
- **Chi tiết theo ID:** `GET /api/v1/items/{item_id}`
