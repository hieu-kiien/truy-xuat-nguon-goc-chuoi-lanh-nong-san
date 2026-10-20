"""Service for the caller's own organization (N3-57, N3-30)."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.identity import Organization
from app.schemas.organization import ContactEmailUpdate, OrganizationRead


def read_my_organization(db: Session, principal: Principal) -> OrganizationRead:
    """Return the organization of the signed-in user."""
    organization = db.get(Organization, principal.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tổ chức của bạn.",
        )
    return OrganizationRead.model_validate(organization)


def update_contact_email(
    db: Session, principal: Principal, payload: ContactEmailUpdate
) -> OrganizationRead:
    """Set the official contact address of the caller's organization."""
    organization = db.get(Organization, principal.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tổ chức của bạn.",
        )
    organization.contact_email = payload.contact_email
    db.commit()
    db.refresh(organization)
    return OrganizationRead.model_validate(organization)
