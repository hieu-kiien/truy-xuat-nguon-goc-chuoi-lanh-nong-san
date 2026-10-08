import { Component, type ErrorInfo, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallbackTitle?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo)
  }

  handleReload = (): void => {
    window.location.reload()
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          style={{
            padding: '2rem',
            margin: '1.5rem',
            borderRadius: '8px',
            backgroundColor: 'var(--bg-card, #ffffff)',
            border: '1px solid var(--border-card, #c5e0cd)',
            boxShadow: 'var(--panel-shadow)',
            color: 'var(--text-primary, #111827)',
            fontFamily: 'var(--font-sans, system-ui, sans-serif)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              marginBottom: '1rem',
            }}
          >
            <span style={{ fontSize: '1.5rem' }}>⚠️</span>
            <h2
              style={{
                margin: 0,
                fontSize: '1.25rem',
                color: 'var(--fg-danger, #b91c1c)',
              }}
            >
              {this.props.fallbackTitle ?? 'Đã xảy ra sự cố không mong muốn'}
            </h2>
          </div>
          <p
            style={{
              color: 'var(--text-secondary, #3b5544)',
              marginBottom: '1rem',
              lineHeight: '1.5',
            }}
          >
            Hệ thống đã tự động khoanh vùng và chặn lỗi để bảo vệ phiên làm việc của bạn.
            Bạn có thể thử khôi phục lại bảng điều khiển hoặc tải lại trang.
          </p>
          <div
            style={{
              display: 'flex',
              gap: '0.75rem',
              flexWrap: 'wrap',
              marginBottom: '1rem',
            }}
          >
            <button
              type="button"
              className="ds-button ds-button-brand ds-button-sm"
              onClick={this.handleReset}
            >
              Thử lại phân hệ này
            </button>
            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm"
              onClick={this.handleReload}
            >
              Tải lại toàn bộ trang
            </button>
          </div>
          {this.state.error && (
            <details style={{ marginTop: '1rem', fontSize: '0.8125rem' }}>
              <summary
                style={{
                  cursor: 'pointer',
                  color: 'var(--text-secondary, #3b5544)',
                }}
              >
                Chi tiết kỹ thuật (dành cho bộ phận hỗ trợ)
              </summary>
              <pre
                style={{
                  marginTop: '0.5rem',
                  padding: '0.75rem',
                  backgroundColor: 'var(--bg-secondary, #f0f7f2)',
                  borderRadius: '6px',
                  overflowX: 'auto',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono, monospace)',
                }}
              >
                {this.state.error.message}
                {'\n'}
                {this.state.error.stack}
              </pre>
            </details>
          )}
        </div>
      )
    }

    return this.props.children
  }
}
