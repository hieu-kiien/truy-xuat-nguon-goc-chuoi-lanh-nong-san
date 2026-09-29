import { useState, useEffect } from 'react'
import { checkHealth } from './services/api'

export default function App() {
  const [healthStatus, setHealthStatus] = useState<string>('Đang kiểm tra kết nối Backend...')
  const [isConnected, setIsConnected] = useState<boolean | null>(null)

  useEffect(() => {
    checkHealth()
      .then((res) => {
        setHealthStatus(res.message || 'Kết nối thành công!')
        setIsConnected(true)
      })
      .catch(() => {
        setHealthStatus('Chưa kết nối được Backend (hãy đảm bảo Backend đang chạy ở port 8000)')
        setIsConnected(false)
      })
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', padding: '2rem', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
      <h1>🌾 TTCS — Nông Sản Chuỗi Lạnh</h1>
      <p style={{ color: '#666', fontSize: '1.1rem' }}>Hệ thống quản lý và truy xuất nguồn gốc nông sản</p>

      <div style={{
        marginTop: '2rem',
        padding: '1.5rem',
        borderRadius: '8px',
        backgroundColor: isConnected === true ? '#e6f7ed' : isConnected === false ? '#ffebe9' : '#f0f0f0',
        border: `1px solid ${isConnected === true ? '#52c41a' : isConnected === false ? '#ff4d4f' : '#d9d9d9'}`
      }}>
        <h3>Trạng thái kết nối Hệ thống</h3>
        <p style={{ fontWeight: '500', color: isConnected === true ? '#237804' : isConnected === false ? '#a8071a' : '#333' }}>
          {healthStatus}
        </p>
      </div>

      <div style={{ marginTop: '2rem', textAlign: 'left', backgroundColor: '#fafafa', padding: '1rem 1.5rem', borderRadius: '8px' }}>
        <h4>📌 Hướng dẫn cho nhóm phát triển:</h4>
        <ul style={{ lineHeight: '1.8' }}>
          <li><strong>API Swagger Backend:</strong> <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">http://localhost:8000/docs</a></li>
          <li><strong>Quy ước code & Git:</strong> Xem file <code>CONTRIBUTING.md</code></li>
          <li><strong>Gọi API mới:</strong> Thêm hàm vào <code>src/services/api.ts</code></li>
        </ul>
      </div>
    </div>
  )
}
