import { useEffect, useRef, useState, type RefObject } from 'react'
import { getCurrentUser } from '../services/api'
import { ORG_TYPE_LABELS, ROLE_LABELS, type RoleCode, type SessionUser } from '../types'

/**
 * Bảng ánh xạ vai trò tiếng Việt trang trọng, ngắn gọn theo tài liệu thiết kế:
 * nông hộ, hợp tác xã, vận chuyển, phân phối, quản trị, thanh tra.
 */
const PROFILE_ROLE_LABELS: Record<RoleCode, string> = {
  grower: 'Nông hộ',
  cooperative: 'Hợp tác xã',
  transporter: 'Vận chuyển',
  distributor: 'Phân phối',
  inspector: 'Thanh tra',
  organization_admin: 'Quản trị đơn vị',
  system_admin: 'Quản trị hệ thống',
}

export interface ProfileModalProps {
  user: SessionUser
  onClose: () => void
  onLogout?: () => void
  triggerRef?: RefObject<HTMLElement | null>
}

export function ProfileModal({ user, onClose, onLogout, triggerRef }: ProfileModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const closeBtnRef = useRef<HTMLButtonElement>(null)
  const [profileUser, setProfileUser] = useState<SessionUser>(user)
  const [refreshing, setRefreshing] = useState(false)

  // Mở hộp thoại modal và ghi nhớ phần tử focus trước đó để trả lại khi đóng
  useEffect(() => {
    const triggerElement = triggerRef?.current
    const previousFocus = (document.activeElement as HTMLElement) || triggerElement
    const dialog = dialogRef.current

    if (dialog) {
      if (typeof dialog.showModal === 'function') {
        try {
          dialog.showModal()
        } catch {
          // Bỏ qua nếu đã mở hoặc trong môi trường test SSR/mock
        }
      }
      closeBtnRef.current?.focus()
    }

    return () => {
      if (dialog && typeof dialog.close === 'function') {
        try {
          dialog.close()
        } catch {
          // Bỏ qua nếu đã đóng
        }
      }
      if (triggerElement && typeof triggerElement.focus === 'function') {
        triggerElement.focus()
      } else if (previousFocus && typeof previousFocus.focus === 'function') {
        previousFocus.focus()
      }
    }
  }, [triggerRef])

  // Xử lý phím: Esc để đóng và Tab trap khép kín bên trong modal
  const handleKeyDown = (event: React.KeyboardEvent<HTMLDialogElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      onClose()
      return
    }

    if (event.key === 'Tab') {
      const dialog = dialogRef.current
      if (!dialog) return

      const focusable = dialog.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
  }

  // Tùy chọn làm mới thông tin phiên bằng API service (không gọi fetch trực tiếp)
  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const fresh = await getCurrentUser()
      if (fresh) {
        setProfileUser(fresh)
      }
    } catch {
      // Giữ nguyên dữ liệu phiên hiện có nếu không kết nối được
    } finally {
      setRefreshing(false)
    }
  }

  const roleLabel =
    PROFILE_ROLE_LABELS[profileUser.role] ?? ROLE_LABELS[profileUser.role] ?? profileUser.role
  const orgTypeLabel =
    ORG_TYPE_LABELS[profileUser.organization_type] ?? profileUser.organization_type
  const initials = profileUser.full_name
    ? profileUser.full_name.trim().charAt(0).toUpperCase()
    : 'U'

  return (
    <dialog
      ref={dialogRef}
      className="edit-dialog profile-modal-dialog"
      aria-labelledby="profile-modal-title"
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
      onKeyDown={handleKeyDown}
    >
      <div className="edit-dialog-header profile-modal-header">
        <div className="profile-header-title-wrap">
          <h2 id="profile-modal-title" className="profile-modal-heading">
            Hồ sơ tài khoản
          </h2>
          <span className="profile-session-pill">Phiên đăng nhập</span>
        </div>
        <button
          ref={closeBtnRef}
          type="button"
          className="ds-button ds-button-secondary profile-close-btn"
          onClick={onClose}
          aria-label="Đóng hộp thoại hồ sơ"
        >
          Đóng
        </button>
      </div>

      <div className="profile-modal-body">
        {/* Khối tóm tắt thông tin người dùng với Avatar lớn */}
        <div className="profile-hero-card">
          <div className="profile-hero-avatar-large" aria-hidden="true">
            <span>{initials}</span>
          </div>
          <div className="profile-hero-info">
            <div className="profile-hero-name">{profileUser.full_name}</div>
            <div className="profile-hero-email">{profileUser.email}</div>
            <div className="profile-badges-row">
              <span className="profile-role-badge">
                Vai trò: {roleLabel}
              </span>
              <span className="profile-org-badge">
                {orgTypeLabel}
              </span>
            </div>
          </div>
        </div>

        {/* Danh sách trường dữ liệu chi tiết */}
        <div className="profile-detail-section">
          <h3 className="profile-section-title">Chi tiết tài khoản</h3>
          <dl className="profile-data-list">
            <div className="profile-data-row">
              <dt className="profile-data-label">Họ và tên</dt>
              <dd className="profile-data-value">{profileUser.full_name}</dd>
            </div>

            <div className="profile-data-row">
              <dt className="profile-data-label">Địa chỉ email</dt>
              <dd className="profile-data-value profile-mono-text">{profileUser.email}</dd>
            </div>

            <div className="profile-data-row">
              <dt className="profile-data-label">Vai trò hệ thống</dt>
              <dd className="profile-data-value">
                <strong>{roleLabel}</strong>
                <span className="profile-code-sub"> ({profileUser.role})</span>
              </dd>
            </div>

            <div className="profile-data-row">
              <dt className="profile-data-label">Đơn vị công tác</dt>
              <dd className="profile-data-value">{profileUser.organization_name}</dd>
            </div>

            <div className="profile-data-row">
              <dt className="profile-data-label">Loại hình tổ chức</dt>
              <dd className="profile-data-value">{orgTypeLabel}</dd>
            </div>

            <div className="profile-data-row">
              <dt className="profile-data-label">Mã định danh</dt>
              <dd className="profile-data-value profile-mono-text profile-id-text">{profileUser.id}</dd>
            </div>
          </dl>
        </div>

        {/* Các nút thao tác phía dưới */}
        <div className="profile-modal-actions">
          <button
            type="button"
            className="ds-button ds-button-secondary ds-button-sm profile-refresh-btn"
            onClick={() => void handleRefresh()}
            disabled={refreshing}
          >
            {refreshing ? 'Đang tải lại…' : 'Làm mới thông tin'}
          </button>

          {onLogout && (
            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm profile-logout-btn"
              onClick={() => {
                onClose()
                onLogout()
              }}
            >
              Đăng xuất phiên
            </button>
          )}
        </div>
      </div>
    </dialog>
  )
}
