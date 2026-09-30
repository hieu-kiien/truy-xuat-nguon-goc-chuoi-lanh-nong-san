"""Create one organization-scoped admin for local development demos."""

import os

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.identity import Organization, Role, User


def seed_demo_admin() -> None:
    email = os.getenv("DEMO_ADMIN_EMAIL", "admin@gmail.com").strip().casefold()
    password = os.getenv("DEMO_ADMIN_PASSWORD", "")
    system_email = (
        os.getenv("SYSTEM_ADMIN_EMAIL", "admin@ttcs.local").strip().casefold()
    )
    system_password = os.getenv("SYSTEM_ADMIN_PASSWORD", "")
    if settings.APP_ENV == "development" and not password:
        raise RuntimeError("DEMO_ADMIN_PASSWORD must be set in development")
    if settings.APP_ENV == "development" and len(password) < 12:
        raise RuntimeError("DEMO_ADMIN_PASSWORD must contain at least 12 characters")
    if system_password and len(system_password) < 12:
        raise RuntimeError("SYSTEM_ADMIN_PASSWORD must contain at least 12 characters")
    if system_password and system_email == email:
        raise RuntimeError("SYSTEM_ADMIN_EMAIL and DEMO_ADMIN_EMAIL must be different")
    if settings.APP_ENV != "development" and not system_password:
        return

    with SessionLocal.begin() as db:
        organization = db.scalar(
            select(Organization).where(
                Organization.name == "Tổ chức quản trị demo",
                Organization.organization_type == "administration",
            )
        )
        if organization is None:
            organization = Organization(
                name="Tổ chức quản trị demo",
                organization_type="administration",
                is_active=True,
            )
            db.add(organization)
            db.flush()
        db.execute(
            select(
                func.set_config("app.current_organization", str(organization.id), True)
            )
        )

        if system_password:
            db.execute(select(func.set_config("app.login_email", system_email, True)))
            system_user = db.scalar(select(User).where(User.email == system_email))
            if system_user is None:
                system_role = db.get(Role, "system_admin")
                if system_role is None:
                    raise RuntimeError(
                        "system_admin role is missing; run migrations first"
                    )
                db.add(
                    User(
                        organization_id=organization.id,
                        role_code=system_role.code,
                        email=system_email,
                        full_name="System Admin",
                        password_hash=hash_password(system_password),
                        failed_login_attempts=0,
                        is_active=True,
                    )
                )
                print(f"Created system admin: {system_email}")
            else:
                print(
                    f"System admin {system_email} already exists; leaving it unchanged."
                )

        if settings.APP_ENV != "development":
            return

        db.execute(select(func.set_config("app.login_email", email, True)))
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            print(f"Demo admin {email} already exists; leaving it unchanged.")
            return

        role = db.get(Role, "organization_admin")
        if role is None:
            raise RuntimeError(
                "organization_admin role is missing; run migrations first"
            )

        legacy_email = "admin@review-agri.org"
        db.execute(select(func.set_config("app.login_email", legacy_email, True)))
        user = db.scalar(select(User).where(User.email == legacy_email))
        if user is not None:
            db.execute(
                select(
                    func.set_config(
                        "app.current_organization", str(user.organization_id), True
                    )
                )
            )
            user.email = email
            user.full_name = "Admin Demo"
            user.role_code = role.code
            user.failed_login_attempts = 0
            user.locked_until = None
            user.is_active = True
            print(f"Renamed existing demo admin to {email}.")
            return

        db.add(
            User(
                organization_id=organization.id,
                role_code=role.code,
                email=email,
                full_name="Admin Demo",
                password_hash=hash_password(password),
                failed_login_attempts=0,
                is_active=True,
            )
        )
        print(f"Created development demo admin: {email}")


if __name__ == "__main__":
    seed_demo_admin()
