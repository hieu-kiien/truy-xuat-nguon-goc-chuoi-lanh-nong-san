import { useState } from 'react'

interface ColdChainPipelineProps {
  tamperSimulated?: boolean
  currentStageIndex?: number
  onStageClick?: (stageId: string) => void
}

interface PipelineStage {
  id: string
  seq: string
  title: string
  subtitle: string
  temp: string
  status: 'normal' | 'active' | 'warning' | 'done'
  icon: string
}

export function ColdChainPipeline({
  tamperSimulated = false,
  currentStageIndex = 3,
  onStageClick,
}: ColdChainPipelineProps) {
  const [selectedStage, setSelectedStage] = useState<string | null>(null)

  const stages: PipelineStage[] = [
    {
      id: 'origin',
      seq: '01',
      title: 'Vùng trồng',
      subtitle: 'Định vị GPS WGS84',
      temp: '18.5°C',
      status: 'done',
      icon: '🌱',
    },
    {
      id: 'harvest',
      seq: '02',
      title: 'Thu hoạch',
      subtitle: 'Phân loại & Niêm phong',
      temp: '14.2°C',
      status: 'done',
      icon: '🌾',
    },
    {
      id: 'precool',
      seq: '03',
      title: 'Cấp đông nhanh',
      subtitle: 'Hạ nhiệt sơ bộ',
      temp: '3.8°C',
      status: 'done',
      icon: '❄️',
    },
    {
      id: 'transport',
      seq: '04',
      title: 'Vận chuyển xe lạnh',
      subtitle: tamperSimulated ? 'Vi phạm nhiệt độ!' : 'Giám sát hành trình IoT',
      temp: tamperSimulated ? '99.9°C' : '3.5°C',
      status: tamperSimulated ? 'warning' : 'active',
      icon: '🚛',
    },
    {
      id: 'distribution',
      seq: '05',
      title: 'Kho phân phối',
      subtitle: tamperSimulated ? 'Đứt chuỗi xác minh' : 'Đối soát mã băm nhập kho',
      temp: '4.0°C',
      status: tamperSimulated ? 'warning' : currentStageIndex >= 4 ? 'done' : 'active',
      icon: '🏬',
    },
  ]

  const handleStageSelect = (stageId: string) => {
    setSelectedStage((prev) => (prev === stageId ? null : stageId))
    onStageClick?.(stageId)
  }

  return (
    <section className="pipeline-card panel-card" aria-label="Quy trình chuỗi lạnh nông sản">
      <div className="pipeline-header">
        <div className="pipeline-title-group">
          <span className="pipeline-badge">
            <span className="telemetry-live-dot" aria-hidden="true" />
            Hành trình Chuỗi cung ứng Lạnh
          </span>
          <span className="pipeline-sub">
            Mô hình hóa dòng chảy nông sản từ nông trại tới quầy kệ có bảo chứng nhiệt độ
          </span>
        </div>

        <div className="pipeline-telemetry-tag">
          <span className="telemetry-chill-pill">
            <span
              className={`chill-pulse-indicator ${tamperSimulated ? 'chill-danger' : 'chill-optimal'}`}
            />
            Chuỗi lạnh: {tamperSimulated ? 'CẢNH BÁO ĐỨT GÃY' : 'CHUẨN 0°C – 4°C'}
          </span>
        </div>
      </div>

      <div className="pipeline-track">
        {stages.map((stage, idx) => {
          const isSelected = selectedStage === stage.id
          const isWarning = tamperSimulated && (stage.id === 'transport' || stage.id === 'distribution')
          const isLast = idx === stages.length - 1

          return (
            <div key={stage.id} className="pipeline-step-wrapper">
              <button
                type="button"
                className={`pipeline-step-node ${isWarning ? 'step-warning' : ''} ${
                  isSelected ? 'step-selected' : ''
                }`}
                onClick={() => handleStageSelect(stage.id)}
                title={`Bấm để xem chi tiết chặng: ${stage.title}`}
              >
                <div className="step-node-header">
                  <span className="step-node-seq">{stage.seq}</span>
                  <span className="step-node-icon" aria-hidden="true">
                    {stage.icon}
                  </span>
                  <span
                    className={`step-temp-badge ${
                      isWarning ? 'temp-danger' : stage.id === 'precool' || stage.id === 'transport' ? 'temp-chill' : ''
                    }`}
                  >
                    {stage.temp}
                  </span>
                </div>

                <div className="step-node-body">
                  <strong className="step-node-title">{stage.title}</strong>
                  <span className="step-node-sub">{stage.subtitle}</span>
                </div>
              </button>

              {!isLast && (
                <div
                  className={`pipeline-connector ${
                    tamperSimulated && idx === 3 ? 'connector-broken' : 'connector-active'
                  }`}
                  aria-hidden="true"
                >
                  <div className="connector-line">
                    <span className="connector-particle" />
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
