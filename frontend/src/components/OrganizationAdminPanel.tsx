import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  createOrganizationInvitation,
  deactivateOrganizationMember,
  getOrganizationInvitations,
  getOrganizationMembers,
  getMyOrganization,
  revokeOrganizationInvitation,
  updateContactEmail,
} from '../services/api'
import type {
  OrganizationInvitation,
  OrganizationMember,
  OrganizationProfile,
} from '../types'

const INVITATION_STATUS_LABELS: Record<string, string> = {
  pending: 'Chờ xác nhận',
  accepted: 'Đã dùng',
  revoked: 'Đã thu hồi',
  expired: 'Đã hết hạn',
}

const INVITABLE_ROLES = [
  { code: 'grower', label: 'Nông hộ / Trang trại' },
  { code: 'cooperative', label: 'Hợp tác xã' },
  { code: 'transporter', label: 'Đơn vị vận chuyển' },
  { code: 'distributor', label: 'Nhà phân phối' },
  { code: 'inspector', label: 'Cơ quan kiểm tra' },
  { code: 'organization_admin', label: 'Quản trị tổ chức' },
]

export function OrganizationAdminPanel({
  canManage = true,
}: {
  canManage?: boolean
}) {
  const [organization, setOrganization] = useState<OrganizationProfile | null>(
    null,
  )
  const [members, setMembers] = useState<OrganizationMember[]>([])
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([])
  const [contactEmail, setContactEmail] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('grower')
  const [invitationUrl, setInvitationUrl] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [inviting, setInviting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [profile, memberList, invitationList] = await Promise.all([
        getMyOrganization(),
        getOrganizationMembers(),
        canManage ? getOrganizationInvitations() : Promise.resolve([]),
      ])
      setOrganization(profile)
      setContactEmail(profile.contact_email ?? '')
      setMembers(memberList)
      setInvitations(invitationList)
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể tải thông tin tổ chức.',
      )
    }
  }, [canManage])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load()
    }, 150)
    return () => {
      window.clearTimeout(timer)
    }
  }, [load])

  const saveContactEmail = async (event: FormEvent) => {
    event.preventDefault()
    if (saving) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const updated = await updateContactEmail(contactEmail)
      setOrganization(updated)
      setContactEmail(updated.contact_email ?? '')
      setNotice('Đã lưu địa chỉ email đầu mối của tổ chức.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể lưu địa chỉ email.')
    } finally {
      setSaving(false)
    }
  }

  const invite = async (event: FormEvent) => {
    event.preventDefault()
    if (inviting) return
    setInviting(true)
    setError(null)
    setNotice(null)
    setInvitationUrl(null)
    try {
      const created = await createOrganizationInvitation({
        email: inviteEmail.trim(),
        role_code: inviteRole,
      })
      setInvitationUrl(created.invitation_url)
      setInviteEmail('')
      setNotice(`Đã gửi lời mời tới ${created.email}.`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tạo lời mời.')
    } finally {
      setInviting(false)
    }
  }

  const revoke = async (invitationId: string) => {
    setError(null)
    setNotice(null)
    try {
      await revokeOrganizationInvitation(invitationId)
      setNotice('Đã thu hồi lời mời.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể thu hồi lời mời.')
    }
  }

  const deactivate = async (memberId: string, memberName: string) => {
    setError(null)
    setNotice(null)
    if (
      !window.confirm(
        `Vô hiệu hoá tài khoản của ${memberName}? Người này sẽ không đăng nhập được nữa.`,
      )
    ) {
      return
    }
    try {
      await deactivateOrganizationMember(memberId)
      setNotice(`Đã vô hiệu hoá thành viên ${memberName}.`)
      await load()
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể vô hiệu hoá thành viên.',
      )
    }
  }

  return (
    <section className="panel-card panel-box" aria-label="Quản trị tổ chức">
      <header className="panel-head">
        <div>
          <h2>Quản trị tổ chức</h2>
          <p className="panel-sub">
            Địa chỉ email đầu mối nhận thông báo thu hồi, danh sách thành viên và
            các lời mời đang chờ.
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

      {organization && (
        <p>
          Tổ chức: <strong>{organization.name}</strong> (
          {organization.organization_type})
        </p>
      )}

      {canManage && (
        <form onSubmit={saveContactEmail} className="integrity-check-controls">
          <div className="form-field">
            <label htmlFor="organization-contact-email">Email đầu mối</label>
            <input
              id="organization-contact-email"
              type="email"
              value={contactEmail}
              onChange={(event) => setContactEmail(event.target.value)}
              placeholder="vanphong@example.com"
            />
          </div>
          <button type="submit" className="ds-button ds-button-brand" disabled={saving}>
            {saving ? 'Đang lưu…' : 'Lưu'}
          </button>
        </form>
      )}

      {canManage && (
        <>
          <h3>Mời thành viên mới</h3>
          <form onSubmit={invite} className="integrity-check-controls">
            <div className="form-field">
              <label htmlFor="organization-invite-email">Email được mời</label>
              <input
                id="organization-invite-email"
                type="email"
                required
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
                placeholder="colleague@example.com"
              />
            </div>
            <div className="form-field">
              <label htmlFor="organization-invite-role">Vai trò</label>
              <select
                id="organization-invite-role"
                value={inviteRole}
                onChange={(event) => setInviteRole(event.target.value)}
              >
                {INVITABLE_ROLES.map((role) => (
                  <option key={role.code} value={role.code}>
                    {role.label}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="ds-button ds-button-brand" disabled={inviting}>
              {inviting ? 'Đang gửi…' : 'Gửi lời mời'}
            </button>
          </form>

          {invitationUrl && (
            <div className="alert-box alert-info" role="status">
              <p>Link mời dùng một lần, hết hạn sau 72 giờ:</p>
              <code>{invitationUrl}</code>
            </div>
          )}

          <h3>Lời mời ({invitations.length})</h3>
          {invitations.length === 0 ? (
            <p>Chưa có lời mời nào.</p>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Email</th>
                    <th scope="col">Vai trò</th>
                    <th scope="col">Trạng thái</th>
                    <th scope="col">Hết hạn</th>
                    <th scope="col">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {invitations.map((invitation) => (
                    <tr key={invitation.id}>
                      <td>{invitation.email}</td>
                      <td>{invitation.role_code}</td>
                      <td>
                        <span className="status-badge">
                          {INVITATION_STATUS_LABELS[invitation.status] ??
                            invitation.status}
                        </span>
                      </td>
                      <td>
                        {new Date(invitation.expires_at).toLocaleString('vi-VN')}
                      </td>
                      <td>
                        {invitation.status === 'pending' && (
                          <button
                            type="button"
                            className="ds-button ds-button-secondary ds-button-xs"
                            onClick={() => void revoke(invitation.id)}
                          >
                            Thu hồi
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <h3>Thành viên ({members.length})</h3>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Họ tên</th>
              <th scope="col">Email</th>
              <th scope="col">Vai trò</th>
              <th scope="col">Trạng thái</th>
              {canManage && <th scope="col">Thao tác</th>}
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id}>
                <td>{member.full_name}</td>
                <td>{member.email}</td>
                <td>{member.role_code}</td>
                <td>
                  <span className="status-badge">
                    {member.is_active ? 'Đang hoạt động' : 'Đã vô hiệu hoá'}
                  </span>
                </td>
                {canManage && (
                  <td>
                    {member.is_active && (
                      <button
                        type="button"
                        className="ds-button ds-button-secondary ds-button-xs"
                        onClick={() =>
                          void deactivate(member.id, member.full_name)
                        }
                      >
                        Vô hiệu hoá
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
