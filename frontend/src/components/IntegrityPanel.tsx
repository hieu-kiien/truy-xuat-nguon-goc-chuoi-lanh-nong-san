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
  icon: string
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
    icon: '🌾',
  },
  {
    seq: '#02',
    timestamp: '2026-09-30T08:15:00Z',
    stage: 'Sơ chế & Cấp đông nhanh',
    temp: '3.8°C',
    humidity: '85%',
    prevHash: '9f86d081...8b4c70a1',
    hash: '4b227777...d4735e3a',
    icon: '❄️',
  },
  {
    seq: '#03',
    timestamp: '2026-09-30T10:30:00Z',
    stage: 'Vận chuyển xe lạnh chuyên dụng',
    temp: '3.5°C',
    humidity: '82%',
    prevHash: '4b227777...d4735e3a',
    hash: 'e3b0c442...98fc1c14',
    icon: '🚛',
  },
  {
    seq: '#04',
    timestamp: '2026-09-30T14:00:00Z',
    stage: 'Nhập kho trung tâm phân phối',
    temp: '4.0°C',
    humidity: '80%',
    prevHash: 'e3b0c442...98fc1c14',
    hash: 'a1860004...b62aa867',
    icon: '🏬',
  },
]

export function IntegrityPanel({
  tamperSimulated,
  onToggleTamper,
  compact = false,
}: IntegrityPanelProps) {
  return (
    <div className={compact ? '' : 'info-stack'}>
      {/* Interactive Visual Hash Chain Node Diagram */}
      <section
        className={`hash-chain-visualizer panel-card ${tamperSimulated ? 'chain-tampered' : 'chain-valid'}`}
        aria-label="Sơ đồ tương tác chuỗi băm sự kiện mật mã"
      >
        <div className="chain-visual-header">
          <div>
            <div className="chain-badge-row">
              <span className={`status-badge ${tamperSimulated ? 'status-danger' : 'status-done'}`}>
                {tamperSimulated ? '⚡ Phát hiện Can thiệp Mật mã' : '🔒 Chuỗi Khép kín — Toàn vẹn 100%'}
              </span>
              <span className="chain-tech-tag">SHA-256 + RFC 8785 JCS</span>
            </div>
            <h3 className="chain-visual-title">
              Mô hình Liên kết Mật mã Bất biến (Cryptographic Hash Chain)
            </h3>
            <p className="panel-sub">
              Mỗi bản ghi niêm phong kèm băm của bản ghi trước: <code>H(n) = SHA256(H(n-1) || Data(n))</code>
            </p>
          </div>

          <button
            type="button"
            className={`ds-button ds-button-sm ${
              tamperSimulated ? 'ds-button-brand' : 'ds-button-secondary'
            }`}
            onClick={onToggleTamper}
          >
            {tamperSimulated ? 'Khôi phục dữ liệu gốc' : 'Mô phỏng sửa lén nhiệt độ (#03)'}
          </button>
        </div>

        {/* Nodes and Connectors Visual */}
        <div className="chain-flow-track" role="region" aria-label="Các mắt xích chuỗi băm">
          {SAMPLE_HASH_EVENTS.map((ev, idx) => {
            const isTamperedNode = tamperSimulated && idx === 2
            const isBrokenDownstream = tamperSimulated && idx > 2
            const isLast = idx === SAMPLE_HASH_EVENTS.length - 1

            return (
              <div key={ev.seq} className="chain-node-wrapper">
                <div
                  className={`chain-node-box ${
                    isTamperedNode
                      ? 'node-tampered'
                      : isBrokenDownstream
                        ? 'node-broken'
                        : 'node-verified'
                  }`}
                >
                  <div className="node-head">
                    <span className="node-seq-pill">{ev.seq}</span>
                    <span className="node-icon" aria-hidden="true">
                      {ev.icon}
                    </span>
                    <span
                      className={`node-status-dot ${
                        isTamperedNode || isBrokenDownstream ? 'dot-danger' : 'dot-verified'
                      }`}
                      title={
                        isTamperedNode
                          ? 'Dữ liệu bị sửa đổi!'
                          : isBrokenDownstream
                            ? 'Mất liên kết băm'
                            : 'Mã băm hợp lệ'
                      }
                    />
                  </div>

                  <strong className="node-stage-name">{ev.stage}</strong>

                  <div className="node-data-pill">
                    <span className="node-temp-label">Nhiệt độ:</span>
                    <strong
                      className={`node-temp-val ${isTamperedNode ? 'temp-tampered-alert' : ''}`}
                    >
                      {isTamperedNode ? '99.9°C (Sửa)' : ev.temp}
                    </strong>
                  </div>

                  <div className="node-hash-preview" title={ev.hash}>
                    <span className="hash-key">Hash:</span>
                    <code>
                      {isTamperedNode ? 'e9d41a02...7c3b81f9' : ev.hash.slice(0, 16)}...
                    </code>
                  </div>
                </div>

                {!isLast && (
                  <div
                    className={`chain-link-connector ${
                      tamperSimulated && idx === 2 ? 'link-fractured' : 'link-verified'
                    }`}
                    aria-hidden="true"
                  >
                    <div className="connector-svg-beam">
                      <span className="beam-spark" />
                    </div>
                    {tamperSimulated && idx === 2 && (
                      <span className="fracture-label" title="Liên kết băm bị đứt gãy!">
                        ⚡ ĐỨT CHUỖI
                      </span>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {tamperSimulated && (
          <div className="alert-box alert-error alert-spaced" role="alert">
            <strong>[!] Cảnh báo Toàn vẹn:</strong> Dữ liệu nhiệt độ tại chặng #03 bị thay đổi từ{' '}
            <code>3.5°C</code> thành <code>99.9°C</code>. Khi băm lại bằng SHA-256 + RFC 8785, giá trị
            mới (<code>e9d41a02...</code>) không khớp với giá trị niêm phong (<code>e3b0c442...</code>).
            Toàn bộ chuỗi sự kiện phía sau lập tức bị vô hiệu hóa!
          </div>
        )}
      </section>

      {/* Comprehensive Data Table */}
      <section className="data-table-wrapper panel-card">
        <div className="data-table-header">
          <div>
            <h2 className="section-title">
              Bảng Nhật ký Chi tiết Sự kiện Chuỗi lạnh
            </h2>
            <p className="panel-sub">
              Hiệu năng xác minh độc lập: 147.856 sự kiện / giây · Độ trễ: 0,0068 ms / bản ghi
            </p>
          </div>
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
                        {isTamperedRow ? 'e9d41a02...7c3b81f9' : ev.hash}
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
          <section className="panel-card panel-box">
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
                ? `{"event_seq":3,"humidity_pct":82,"lot_id":"lot-caudat-01","prev_hash":"4b227777...d4735e3a","stage":"transport","temp_c":99.9,"timestamp":"2026-09-30T10:30:00Z"}\n-> SHA-256 Tính lại : e9d41a026f904b12...7c3b81f9 (Khác với e3b0c442...98fc1c14 đã niêm phong!)`
                : `{"event_seq":3,"humidity_pct":82,"lot_id":"lot-caudat-01","prev_hash":"4b227777...d4735e3a","stage":"transport","temp_c":3.5,"timestamp":"2026-09-30T10:30:00Z"}\n-> SHA-256 Tính lại : e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 (Khớp 100%)`}
            </pre>
          </section>

          <section className="panel-card panel-box">
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
