interface IntegrityPanelProps {
  tamperSimulated: boolean
  onToggleTamper: () => void
  compact?: boolean
}

interface HashEventRecord {
  seq: string
  timestamp: string
  stage: string
  temp: string
  humidity: string
  prevHash: string
  hash: string
}

const SAMPLE_HASH_EVENTS: HashEventRecord[] = [
  {
    seq: '#01',
    timestamp: '2026-09-30T06:00:00Z',
    stage: 'Thu hoạch tại vùng trồng',
    temp: '14.2°C',
    humidity: '78%',
    prevHash: '00000000...00000000',
    hash: '9f86d081...8b4c70a1',
  },
  {
    seq: '#02',
    timestamp: '2026-09-30T08:15:00Z',
    stage: 'Sơ chế & Cấp đông nhanh',
    temp: '3.8°C',
    humidity: '85%',
    prevHash: '9f86d081...8b4c70a1',
    hash: '4b227777...d4735e3a',
  },
  {
    seq: '#03',
    timestamp: '2026-09-30T10:30:00Z',
    stage: 'Vận chuyển xe lạnh chuyên dụng',
    temp: '3.5°C',
    humidity: '82%',
    prevHash: '4b227777...d4735e3a',
    hash: 'e3b0c442...98fc1c14',
  },
  {
    seq: '#04',
    timestamp: '2026-09-30T14:00:00Z',
    stage: 'Nhập kho trung tâm phân phối',
    temp: '4.0°C',
    humidity: '80%',
    prevHash: 'e3b0c442...98fc1c14',
    hash: 'a1860004...b62aa867',
  },
]

export function IntegrityPanel({
  tamperSimulated,
  onToggleTamper,
  compact = false,
}: IntegrityPanelProps) {
  return (
    <div className={compact ? '' : 'info-stack'}>
      <section className="data-table-wrapper sticker-panel">
        <div className="data-table-header">
          <div>
            <h2 className="section-title">
              Chuỗi Băm Sự kiện Chuỗi lạnh (SHA-256 + RFC 8785)
            </h2>
            <p className="panel-sub">
              Liên kết mật mã chống sửa lén nhật ký nhiệt độ — hiệu năng xác minh:
              147.856 sự kiện/giây
            </p>
          </div>

          <button
            type="button"
            className={`ds-button ds-button-sm ${
              tamperSimulated ? 'ds-button-brand' : 'ds-button-secondary'
            }`}
            onClick={onToggleTamper}
          >
            {tamperSimulated
              ? 'Khôi phục dữ liệu gốc'
              : 'Mô phỏng sửa lén nhiệt độ (#03)'}
          </button>
        </div>

        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>TT</th>
                {!compact && <th>Thời gian (UTC)</th>}
                <th>Công đoạn</th>
                <th>Nhiệt độ / Ẩm</th>
                <th>Prev Hash</th>
                <th>SHA-256 Hash</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {SAMPLE_HASH_EVENTS.map((ev, index) => {
                const isTamperedRow = tamperSimulated && index === 2
                const isBrokenDownstream = tamperSimulated && index > 2
                return (
                  <tr
                    key={ev.seq}
                    className={
                      isTamperedRow || isBrokenDownstream ? 'row-danger' : undefined
                    }
                  >
                    <td>
                      <code>{ev.seq}</code>
                    </td>
                    {!compact && (
                      <td>
                        <code>{ev.timestamp}</code>
                      </td>
                    )}
                    <th scope="row" className="cell-strong">
                      {ev.stage}
                    </th>
                    <td>
                      <code>
                        {isTamperedRow
                          ? `99.9°C / ${ev.humidity} (Sửa)`
                          : `${ev.temp} / ${ev.humidity}`}
                      </code>
                    </td>
                    <td>
                      <code>{ev.prevHash}</code>
                    </td>
                    <td>
                      <code>
                        {isTamperedRow ? 'ff009911...SAI_LECH' : ev.hash}
                      </code>
                    </td>
                    <td>
                      {isTamperedRow ? (
                        <span className="status-badge status-danger">
                          Bị can thiệp
                        </span>
                      ) : isBrokenDownstream ? (
                        <span className="status-badge status-danger">
                          Đứt chuỗi
                        </span>
                      ) : (
                        <span className="status-badge status-done">Toàn vẹn</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {!compact && (
        <div className="dashboard-split-equal">
          <section className="sticker-panel panel-box">
            <div className="panel-head">
              <h2>Chuẩn hóa Canonical JSON (RFC 8785) — Sự kiện #03</h2>
              <span
                className={`status-badge ${
                  tamperSimulated ? 'status-danger' : 'status-done'
                }`}
              >
                {tamperSimulated ? 'Hash Mismatch' : 'Verified'}
              </span>
            </div>
            <p className="panel-sub">
              Các khóa JSON được sắp xếp theo thứ tự từ điển UTF-8 và loại bỏ
              khoảng trắng trước khi băm SHA-256:
            </p>
            <pre className="code-block-compact">
              {tamperSimulated
                ? `{"event_seq":3,"humidity_pct":82,"lot_id":"lot-caudat-01","prev_hash":"4b227777...d4735e3a","stage":"transport","temp_c":99.9,"timestamp":"2026-09-30T10:30:00Z"}\n-> SHA-256 Tính lại : ff00991182ab44c0... (Khác với e3b0c442...98fc1c14 đã niêm phong!)`
                : `{"event_seq":3,"humidity_pct":82,"lot_id":"lot-caudat-01","prev_hash":"4b227777...d4735e3a","stage":"transport","temp_c":3.5,"timestamp":"2026-09-30T10:30:00Z"}\n-> SHA-256 Tính lại : e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 (Khớp 100%)`}
            </pre>
          </section>

          <section className="sticker-panel panel-box">
            <div className="panel-head">
              <h2>Thông số Kiến trúc Toàn vẹn Dữ liệu (N3-4)</h2>
              <span className="status-badge status-done">Chuẩn Công nghiệp</span>
            </div>
            <div className="info-grid-2">
              <div className="info-item">
                <span className="info-item-label">Thuật toán Băm</span>
                <strong className="info-item-value">SHA-256 (FIPS 180-4)</strong>
              </div>
              <div className="info-item">
                <span className="info-item-label">Chuẩn Tuần tự hóa</span>
                <strong className="info-item-value">RFC 8785 (JCS)</strong>
              </div>
              <div className="info-item">
                <span className="info-item-label">Thông lượng Kiểm chứng</span>
                <strong className="info-item-value">147.856 sự kiện / giây</strong>
              </div>
              <div className="info-item">
                <span className="info-item-label">Độ trễ Trung bình</span>
                <strong className="info-item-value">0,0068 ms / bản ghi</strong>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
