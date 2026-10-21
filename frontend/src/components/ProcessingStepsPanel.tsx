import { useCallback, useEffect, useState } from 'react'
import {
  getLotProcessingSteps,
  getProcessingStepCatalogue,
  recordLotProcessingStep,
} from '../services/api'
import type { ProcessingStep, ProcessingStepRecord } from '../types'

interface ProcessingStepsPanelProps {
  lotId: string
  canRecord: boolean
}

export function ProcessingStepsPanel({ lotId, canRecord }: ProcessingStepsPanelProps) {
  const [records, setRecords] = useState<ProcessingStepRecord[]>([])
  const [catalogue, setCatalogue] = useState<ProcessingStep[]>([])
  const [stepId, setStepId] = useState('')
  const [parameters, setParameters] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [recorded, steps] = await Promise.all([
        getLotProcessingSteps(lotId),
        getProcessingStepCatalogue(),
      ])
      setRecords(recorded)
      setCatalogue(steps)
      setStepId((current) => current || steps[0]?.id || '')
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể tải công đoạn chế biến.',
      )
    } finally {
      setLoading(false)
    }
  }, [lotId])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load()
    }, 150)
    return () => {
      window.clearTimeout(timer)
    }
  }, [load])

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!stepId || saving) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const parsed: Record<string, unknown> = {}
      for (const pair of parameters.split(';')) {
        const trimmed = pair.trim()
        if (!trimmed) continue
        const separator = trimmed.indexOf('=')
        if (separator < 0) continue
        const key = trimmed.slice(0, separator).trim()
        const raw = trimmed.slice(separator + 1).trim()
        const numeric = Number(raw)
        parsed[key] = raw !== '' && Number.isFinite(numeric) ? numeric : raw
      }
      await recordLotProcessingStep(lotId, {
        processing_step_id: stepId,
        parameters: parsed,
      })
      setParameters('')
      setNotice('Đã ghi công đoạn chế biến vào chuỗi của lô.')
      await load()
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể ghi công đoạn chế biến.',
      )
    } finally {
      setSaving(false)
    }
  }

  const selected = catalogue.find((step) => step.id === stepId)
  const schema = selected?.parameter_schema ?? {}

  return (
    <section className="panel-card panel-box" aria-label="Công đoạn chế biến của lô">
      <header className="panel-head">
        <div>
          <h2>Công đoạn chế biến</h2>
          <p className="panel-sub">
            Ghi lại công đoạn lô đã qua (rửa, phân loại, đóng gói) kèm tham số.
            Mỗi lần ghi là một sự kiện trong chuỗi của lô.
          </p>
        </div>
      </header>

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="alert-box alert-success" role="status">
          {notice}
        </div>
      )}

      {loading && records.length === 0 && <p role="status">Đang tải công đoạn chế biến…</p>}
      {!loading && records.length === 0 && <p>Chưa ghi công đoạn chế biến nào.</p>}

      {records.length > 0 && (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Công đoạn</th>
                <th scope="col">Tham số</th>
                <th scope="col">Thời điểm</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id}>
                  <td>{record.processing_step_name}</td>
                  <td>
                    {Object.entries(record.parameters)
                      .map(([key, value]) => `${key}: ${String(value)}`)
                      .join(' · ') || '—'}
                  </td>
                  <td>{new Date(record.occurred_at).toLocaleString('vi-VN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {canRecord && (
        <form onSubmit={submit} className="integrity-check-controls">
          <div className="form-field">
            <label htmlFor="processing-step">Công đoạn</label>
            <select
              id="processing-step"
              value={stepId}
              onChange={(event) => setStepId(event.target.value)}
              disabled={catalogue.length === 0}
            >
              {catalogue.length === 0 && <option value="">Danh mục trống</option>}
              {catalogue.map((step) => (
                <option key={step.id} value={step.id}>
                  {step.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label htmlFor="processing-parameters">Tham số</label>
            <input
              id="processing-parameters"
              type="text"
              value={parameters}
              onChange={(event) => setParameters(event.target.value)}
              placeholder={
                Object.keys(schema).length > 0
                  ? Object.keys(schema).join('; ') + '=…'
                  : 'tên=giá trị'
              }
            />
          </div>
          <button
            type="submit"
            className="ds-button ds-button-brand"
            disabled={saving || !stepId}
          >
            {saving ? 'Đang ghi…' : 'Ghi công đoạn'}
          </button>
        </form>
      )}
    </section>
  )
}
