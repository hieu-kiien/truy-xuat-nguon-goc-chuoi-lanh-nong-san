"""Seed initial demo organizations, users, and farms for staging and local development."""

from decimal import Decimal
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.farm import Farm
from app.models.identity import Organization, Role, User

DEMO_ORGANIZATIONS = [
    {
        "id": UUID("11111111-1111-4111-8111-111111111111"),
        "name": "Nông trại Cầu Đất Đà Lạt",
        "organization_type": "farm",
    },
    {
        "id": UUID("22222222-2222-4222-8222-222222222222"),
        "name": "Hợp tác xã Nông sản Mộc Châu",
        "organization_type": "cooperative",
    },
    {
        "id": UUID("33333333-3333-4333-8333-333333333333"),
        "name": "Chi cục Quản lý Chất lượng Nông lâm sản",
        "organization_type": "inspection",
    },
]

DEMO_USERS = [
    {
        "id": UUID("aaaa1111-1111-4111-8111-111111111111"),
        "organization_id": UUID("11111111-1111-4111-8111-111111111111"),
        "role_code": "grower",
        "email": "grower@caudat.vn",
        "full_name": "Nguyễn Văn Minh (Nông hộ Cầu Đất)",
    },
    {
        "id": UUID("bbbb2222-2222-4222-8222-222222222222"),
        "organization_id": UUID("22222222-2222-4222-8222-222222222222"),
        "role_code": "organization_admin",
        "email": "admin@mocchau.vn",
        "full_name": "Trần Thị Hương (Quản trị HTX Mộc Châu)",
    },
    {
        "id": UUID("cccc3333-3333-4333-8333-333333333333"),
        "organization_id": UUID("33333333-3333-4333-8333-333333333333"),
        "role_code": "inspector",
        "email": "inspector@chicuc.gov.vn",
        "full_name": "Lê Hoàng Nam (Thanh tra viên)",
    },
]

DEMO_FARMS = [
    {
        "id": UUID("f1111111-1111-4111-8111-111111111111"),
        "organization_id": UUID("11111111-1111-4111-8111-111111111111"),
        "name": "Khu nhà kính Dâu tây Công nghệ cao A1",
        "area_ha": Decimal("2.4500"),
        "latitude": Decimal("11.862450"),
        "longitude": Decimal("108.538120"),
    },
    {
        "id": UUID("f2222222-2222-4222-8222-222222222222"),
        "organization_id": UUID("11111111-1111-4111-8111-111111111111"),
        "name": "Thửa đất Rau thủy canh Đà Lạt B2",
        "area_ha": Decimal("1.8000"),
        "latitude": Decimal("11.865100"),
        "longitude": Decimal("108.541300"),
    },
    {
        "id": UUID("f3333333-3333-4111-8111-111111111111"),
        "organization_id": UUID("22222222-2222-4222-8222-222222222222"),
        "name": "Vùng trồng Chè Shan Tuyết Mộc Châu C1",
        "area_ha": Decimal("5.2000"),
        "latitude": Decimal("20.844500"),
        "longitude": Decimal("104.639200"),
    },
]


def seed_demo_data() -> None:
    engine = create_engine(settings.MIGRATION_DATABASE_URL, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            if session.scalar(select(Role.code).limit(1)) is None:
                return

            # Demo accounts are entered through /auth/demo-login. Their ordinary
            # password is intentionally random and discarded so no reusable demo
            # password is shipped in source code or the frontend bundle.
            disabled_demo_password_hash = hash_password(token_urlsafe(48))

            for org_data in DEMO_ORGANIZATIONS:
                org = session.get(Organization, org_data["id"])
                if org is None:
                    session.add(
                        Organization(
                            id=org_data["id"],
                            name=org_data["name"],
                            organization_type=org_data["organization_type"],
                            is_active=True,
                        )
                    )

            session.flush()

            for user_data in DEMO_USERS:
                existing_user = session.scalar(
                    select(User).where(User.email == user_data["email"])
                )
                if existing_user is None:
                    session.add(
                        User(
                            id=user_data["id"],
                            organization_id=user_data["organization_id"],
                            role_code=user_data["role_code"],
                            email=user_data["email"],
                            full_name=user_data["full_name"],
                            password_hash=disabled_demo_password_hash,
                            failed_login_attempts=0,
                            locked_until=None,
                            is_active=True,
                        )
                    )
                else:
                    existing_user.password_hash = disabled_demo_password_hash
                    existing_user.failed_login_attempts = 0
                    existing_user.locked_until = None

            session.flush()

            for farm_data in DEMO_FARMS:
                existing_farm = session.get(Farm, farm_data["id"])
                if existing_farm is None:
                    session.add(
                        Farm(
                            id=farm_data["id"],
                            organization_id=farm_data["organization_id"],
                            name=farm_data["name"],
                            area_ha=farm_data["area_ha"],
                            latitude=farm_data["latitude"],
                            longitude=farm_data["longitude"],
                        )
                    )

            session.commit()
    finally:
        engine.dispose()


if __name__ == "__main__":
    seed_demo_data()
