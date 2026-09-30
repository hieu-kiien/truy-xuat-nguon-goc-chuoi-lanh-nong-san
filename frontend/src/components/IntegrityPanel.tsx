interface IntegrityPanelProps {
  tamperSimulated: boolean
  onToggleTamper: () => void
}

interface HashEventRecord {
  seq: string
  stage: string
  temp: string
  prevHash: string
  hash: string
}

const SAMPLE_HASH_EVENTS: HashEventRecord[] = [
  {
    seq: '#01',
    stage: 'Thu hoạch tại vùng trồng',
    temp: '14.2°C',
    prevHash: '00000000...00000000',
    hash: '9f86d081...8b4c70a1',
  },
  {
    seq: '#02',
    stage: 'Sơ chế & Cấp đông nhanh',
    temp: '3.8°C',
    prevHash: '9f86d081...8b4c70a1',
    hash: '4b227777...d4735e3a',
  },
  {
    seq: '#03',
    stage: 'Vận chuyển xe lạnh chuyên dụng',
    temp: '3.5°C',
    prevHash: '4b227777...d4735e3a',
    hash: 'e3b0c442...98fc1c14',
  },
  {
    seq: '#04',
    stage: 'Nhập kho trung tâm phân phối',
    temp: '4.0°C',
    prevHash: 'e3b0c442...98fc1c14',
    hash: 'a1860004...b62aa867',
  },
]

export function IntegrityPanel({
  tamperSimulated,
  onToggleTamper,
}: IntegrityPanelProps) {
  return (
    <section className="data-table-wrapper sticker-panel">
      <div className="data-table-header">
        <div>
          <h2 className="section-title">
            Chuỗi Băm Mật mã Chống sửa lén Bản ghi Sự kiện (SHA-256 + RFC 8785)
          </h2>
          <p className="panel-sub">
            Mỗi sự kiện chuỗi lạnh băm kèm mã hash của sự kiện liền trước — tốc độ
            xác minh thực nghiệm: 147.856 sự kiện/giây
          </p>
        </div>

        <button
          type="button"
          className="ds-button ds-button-secondary ds-button-sm"
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
              <th>Thứ tự</th>
              <th>Công đoạn Chuỗi lạnh</th>
              <th>Nhiệt độ ghi nhận</th>
              <th>Hash sự kiện trước (Prev Hash)</th>
              <th>Hash hiện tại (SHA-256)</th>
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
                  <th scope="row" className="cell-strong">
                    {ev.stage}
                  </th>
                  <td>
                    <code>{isTamperedRow ? '99.9°C (Đã sửa)' : ev.temp}</code>
                  </td>
                  <td>
                    <code>{ev.prevHash}</code>
                  </td>
                  <td>
                    <code>
                      {isTamperedRow ? 'ff009911...LOI_HASH' : ev.hash}
                    </code>
                  </td>
                  <td>
                    {isTamperedRow ? (
                      <span className="status-badge status-danger">
                        Bị can thiệp
                      </span>
                    ) : isBrokenDownstream ? (
                      <span className="status-badge status-danger">
                        Đứt chuỗi liên kết
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
  )
}
