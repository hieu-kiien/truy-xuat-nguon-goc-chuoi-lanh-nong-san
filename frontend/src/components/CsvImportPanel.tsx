import { useEffect, useRef, useState, type FormEvent } from 'react'
import { API_BASE_URL, getStoredSessionToken, request } from '../services/api'

type Kind = 'products' | 'farms'
interface RowError { line: number; column: string; message: string }
const templates: Record<Kind, string> = {
  products: 'name,unit,price,quantity,description\nRau mẫu,kg,12000,100,Mô tả\n',
  farms: 'organization_id,name,area_ha,latitude,longitude\nUUID_TỔ_CHỨC,Thửa mẫu,1.5,10,106\n',
}

export function CsvImportPanel({ onImported }: { onImported: () => void }) {
  const [kind, setKind] = useState<Kind>('products')
  const [file, setFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [errors, setErrors] = useState<RowError[]>([])
  const inFlight = useRef(false)
  const [organizations, setOrganizations] = useState<Array<{id: string; name: string}>>([])
  const [organizationError, setOrganizationError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    request<Array<{id: string; name: string}>>('/api/v1/imports/organizations').then(result => {if (active) setOrganizations(result)})
      .catch((error: unknown) => {if (active) setOrganizationError(error instanceof Error ? error.message : 'Không tải được mã tổ chức.')})
    return () => {active = false}
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!file || inFlight.current) return
    setMessage(null); setErrors([])
    if (file.size > 1024 * 1024) { setMessage('Tệp vượt giới hạn 1 MiB.'); return }
    inFlight.current = true; setSaving(true)
    try {
      const token = getStoredSessionToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/imports/${kind}`, {
        method: 'POST', credentials: 'include', body: file,
        headers: { 'Content-Type': 'text/csv', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      })
      const body = await response.json() as { created?: number; detail?: string | { message?: string; errors?: RowError[] } }
      if (!response.ok) {
        if (typeof body.detail === 'object' && body.detail !== null) {
          setErrors(body.detail.errors ?? []); throw new Error(body.detail.message || 'Không nhập được tệp.')
        }
        throw new Error(typeof body.detail === 'string' ? body.detail : `Lỗi HTTP ${response.status}`)
      }
      setMessage(`Đã nhập ${body.created} dòng thành công.`); onImported()
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : 'Không kết nối được máy chủ.')
    } finally { inFlight.current = false; setSaving(false) }
  }

  return <section className="panel-box panel-card" aria-labelledby="csv-import-title">
    <h2 id="csv-import-title" className="section-title">Nhập danh mục từ CSV</h2>
    <p className="panel-sub">UTF-8, tối đa 1 MiB và 1.000 dòng. Nếu có dòng sai, toàn bộ tệp sẽ không được lưu.</p>
    <form onSubmit={submit}>
      <fieldset disabled={saving} style={{ minWidth: 0, border: 0, padding: 0 }}>
        <div className="form-row-2">
          <div className="form-field"><label htmlFor="csv-kind">Danh mục</label>
            <select id="csv-kind" value={kind} onChange={event => {setKind(event.target.value as Kind); setErrors([]); setMessage(null)}}>
              <option value="products">Sản phẩm</option><option value="farms">Thửa đất</option>
            </select>
          </div>
          <div className="form-field"><label htmlFor="csv-file">Tệp CSV</label>
            <input id="csv-file" type="file" accept=".csv,text/csv" required onChange={event => {setFile(event.target.files?.[0] ?? null); setErrors([]); setMessage(null)}} />
          </div>
        </div>
        <p className="panel-sub">{kind === 'farms' ? 'Thay UUID_TỔ_CHỨC bằng ID nông trại hoặc HTX đang hoạt động.' : 'Đơn vị hợp lệ: kg, tấn, thùng. Giá và số lượng không âm.'}</p>
        <a className="btn-ghost" href={`data:text/csv;charset=utf-8,${encodeURIComponent(templates[kind])}`} download={`${kind}-template.csv`}>Tải mẫu CSV</a>
        <button type="submit" className="btn-primary" disabled={!file}>{saving ? 'Đang nhập…' : 'Nhập toàn bộ tệp'}</button>
      </fieldset>
    </form>
    {kind === 'farms' && <details><summary>Mã nông trại/HTX để điền vào mẫu</summary>
      {organizationError && <p role="alert">{organizationError}</p>}
      <div className="data-table-wrapper"><table><thead><tr><th>Tổ chức</th><th>organization_id</th></tr></thead>
        <tbody>{organizations.map(org => <tr key={org.id}><td>{org.name}</td><td><code>{org.id}</code></td></tr>)}</tbody>
      </table></div>
    </details>}
    {message && <p role="status">{message}</p>}
    {errors.length > 0 && <div className="data-table-wrapper"><table><thead><tr><th>Dòng</th><th>Cột</th><th>Lỗi</th></tr></thead>
      <tbody>{errors.map((error, index) => <tr key={index}><td>{error.line}</td><td>{error.column}</td><td>{error.message}</td></tr>)}</tbody>
    </table></div>}
  </section>
}
