import { useState, useEffect } from 'react'
import { API_BASE_URL, checkHealth } from './services/api'

export default function App() {
  const [statusMessage, setStatusMessage] = useState<string>('Đang kiểm tra kết nối tới máy chủ...')
  const [isConnected, setIsConnected] = useState<boolean | null>(null)

  useEffect(() => {
    checkHealth()
      .then((res) => {
        setStatusMessage(res.message || 'Kết nối máy chủ thành công')
        setIsConnected(true)
      })
      .catch(() => {
        setStatusMessage('Không thể kết nối tới Backend API')
        setIsConnected(false)
      })
  }, [])

  const statusClass =
    isConnected === true
      ? 'status-card status-online'
      : isConnected === false
        ? 'status-card status-offline'
        : 'status-card status-pending'

  return (
    <main className="container">
      <header className="header">
        <h1>Hệ thống Truy xuất Nguồn gốc Chuỗi lạnh Nông sản</h1>
        <p className="subtitle">Nền tảng quản lý lô hàng và giám sát bảo quản nông sản</p>
      </header>

      <section className={statusClass}>
        <h2>Trạng thái kết nối Backend</h2>
        <p className="status-text">{statusMessage}</p>
        <p className="endpoint-info">
          Endpoint: <code>{API_BASE_URL}</code>
        </p>
      </section>

      <section className="info-panel">
        <h3>Tài nguyên phát triển</h3>
        <ul>
          <li>
            <strong>Tài liệu OpenAPI (Swagger):</strong>{' '}
            <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
              {API_BASE_URL}/docs
            </a>
          </li>
          <li>
            <strong>Quy chuẩn đóng góp:</strong> Xem file <code>CONTRIBUTING.md</code> tại thư mục gốc
          </li>
          <li>
            <strong>Tích hợp API:</strong> Định nghĩa các hàm gọi dữ liệu trong <code>src/services/api.ts</code>
          </li>
        </ul>
      </section>
    </main>
  )
}
