"""Kiểm tra chức năng tra cứu lô thu hoạch (GET /api/v1/lots/)."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, set_db_context
from app.main import app
from app.models.audit_log import AuditLog
from app.models.farm import Farm
from app.models.lot import Lot
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


def audit_client() -> AsyncClient:
    """Giống _client nhưng gán IP rõ ràng để kiểm tra nhật ký tra cứu."""
    return AsyncClient(
        transport=ASGITransport(app=app, client=("198.51.100.44", 1234)),
        base_url="https://testserver",
    )


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


def _add_farm(db: Session, organization_id: UUID, name: str) -> Farm:
    farm = Farm(
        organization_id=organization_id,
        name=name,
        area_ha=Decimal("1.2500"),
        latitude=Decimal("10.762622"),
        longitude=Decimal("106.660172"),
    )
    db.add(farm)
    db.commit()
    return farm


def _add_lot(
    db: Session,
    organization_id: UUID,
    farm_id: UUID,
    name: str,
    lot_code: str,
    harvested_on: date,
) -> Lot:
    lot = Lot(
        organization_id=organization_id,
        current_holder_organization_id=organization_id,
        farm_id=farm_id,
        name=name,
        lot_code=lot_code,
        harvested_on=harvested_on,
        quantity=Decimal("10.000"),
        remaining_quantity=Decimal("10.000"),
        status="active",
    )
    db.add(lot)
    db.commit()
    return lot


def _search_rows(db: Session, user_id: UUID) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.actor_user_id == user_id,
                AuditLog.action == "lots.search",
            )
        )
    )


@pytest.mark.asyncio
async def test_search_by_code_and_harvest_window(admin_session, identity_factory):
    owner = identity_factory()
    farm = _add_farm(admin_session, owner.organization_id, "Vùng A")
    _add_lot(
        admin_session,
        owner.organization_id,
        farm.id,
        "Lô 01",
        "SEARCH-01",
        date(2026, 1, 10),
    )
    _add_lot(
        admin_session,
        owner.organization_id,
        farm.id,
        "Lô 02",
        "SEARCH-02",
        date(2026, 1, 15),
    )
    _add_lot(
        admin_session,
        owner.organization_id,
        farm.id,
        "Lô 03",
        "KHAC-03",
        date(2026, 2, 1),
    )

    async with audit_client() as client:
        await _login(client, owner)

        # Tìm theo mã lô (không phân biệt hoa thường)
        page = await client.get("/api/v1/lots/", params={"q": "search"})
        assert page.status_code == 200, page.text
        assert [row["lot_code"] for row in page.json()["items"]] == [
            "SEARCH-02",
            "SEARCH-01",
        ]

        # Khoảng ngày thu hoạch
        page = await client.get(
            "/api/v1/lots/",
            params={"harvested_from": "2026-01-12", "harvested_to": "2026-01-31"},
        )
        assert page.status_code == 200, page.text
        assert [row["lot_code"] for row in page.json()["items"]] == ["SEARCH-02"]

        # Kết hợp mã lô và ngày
        page = await client.get(
            "/api/v1/lots/",
            params={
                "q": "SEARCH-01",
                "harvested_from": "2026-01-01",
                "harvested_to": "2026-12-31",
            },
        )
        assert page.status_code == 200, page.text
        assert [row["lot_code"] for row in page.json()["items"]] == ["SEARCH-01"]

        # Không có kết quả trả trang trống, không lỗi
        page = await client.get("/api/v1/lots/", params={"q": "KHONG-TON-TAI"})
        assert page.status_code == 200
        assert page.json()["items"] == []
        assert page.json()["next_cursor"] is None

    rows = _search_rows(admin_session, owner.user_id)
    assert len(rows) == 4
    assert all(
        r.action == "lots.search"
        and r.object_type == "lot"
        and r.object_id is None
        and r.outcome == "success"
        and r.status_code == 200
        and r.reason is None
        and r.actor_user_id == owner.user_id
        and r.organization_id == owner.organization_id
        and r.actor_authenticated
        and r.client_ip == "198.51.100.44"
        for r in rows
    )


@pytest.mark.asyncio
async def test_search_by_farm_id(admin_session, identity_factory):
    owner = identity_factory()
    farm_a = _add_farm(admin_session, owner.organization_id, "Vùng A")
    farm_b = _add_farm(admin_session, owner.organization_id, "Vùng B")
    _add_lot(
        admin_session,
        owner.organization_id,
        farm_a.id,
        "Lô A",
        "FARM-A-01",
        date(2026, 3, 1),
    )
    _add_lot(
        admin_session,
        owner.organization_id,
        farm_b.id,
        "Lô B",
        "FARM-B-01",
        date(2026, 3, 2),
    )

    async with _client() as client:
        await _login(client, owner)

        page = await client.get("/api/v1/lots/", params={"farm_id": str(farm_b.id)})
        assert page.status_code == 200, page.text
        assert [row["lot_code"] for row in page.json()["items"]] == ["FARM-B-01"]

        # Mã vùng trồng không tồn tại không làm lỗi, chỉ trả rỗng
        page = await client.get("/api/v1/lots/", params={"farm_id": str(uuid4())})
        assert page.status_code == 200
        assert page.json()["items"] == []


@pytest.mark.asyncio
async def test_inspector_reads_across_organizations(admin_session, identity_factory):
    owner = identity_factory()
    other = identity_factory()
    inspector = identity_factory(role="inspector", organization_type="inspection")
    farm1 = _add_farm(admin_session, owner.organization_id, "Vùng chủ sở hữu")
    farm2 = _add_farm(admin_session, other.organization_id, "Vùng đơn vị khác")
    lot1 = _add_lot(
        admin_session,
        owner.organization_id,
        farm1.id,
        "Lô chủ",
        "ISO-01",
        date(2026, 4, 1),
    )
    lot2 = _add_lot(
        admin_session,
        other.organization_id,
        farm2.id,
        "Lô khác",
        "ISO-02",
        date(2026, 4, 2),
    )

    async with audit_client() as client:
        await _login(client, inspector)

        # Thanh tra được xem lô của nhiều tổ chức (lots:read_all)
        page = await client.get("/api/v1/lots/")
        assert page.status_code == 200, page.text
        ids = {row["id"] for row in page.json()["items"]}
        assert {str(lot1.id), str(lot2.id)}.issubset(ids)

        detail = await client.get(f"/api/v1/lots/{lot2.id}")
        assert detail.status_code == 200
        assert detail.json()["organization_id"] == str(other.organization_id)

    # Người dùng thường không thấy lô đang giữ của tổ chức khác, kể cả khi lọc đúng vùng trồng
    async with _client() as client:
        await _login(client, owner)
        page = await client.get("/api/v1/lots/", params={"farm_id": str(farm2.id)})
        assert page.status_code == 200
        assert page.json()["items"] == []

    inspector_rows = [r for r in _search_rows(admin_session, inspector.user_id)]
    assert len(inspector_rows) >= 1
    assert all(r.outcome == "success" and r.status_code == 200 for r in inspector_rows)


@pytest.mark.asyncio
async def test_search_invalid_harvest_window(admin_session, identity_factory):
    owner = identity_factory()
    async with audit_client() as client:
        await _login(client, owner)

        response = await client.get(
            "/api/v1/lots/",
            params={"harvested_from": "2026-06-01", "harvested_to": "2026-01-01"},
        )
        assert response.status_code == 400, response.text
        assert "ngày bắt đầu" in response.json()["detail"]

        # Ngày định dạng sai bị từ chối ở lớp validation
        response = await client.get(
            "/api/v1/lots/", params={"harvested_from": "not-a-date"}
        )
        assert response.status_code == 422

    rows = _search_rows(admin_session, owner.user_id)
    assert len(rows) == 1
    assert rows[0].outcome == "denied"
    assert rows[0].status_code == 400
    assert rows[0].reason == "validation_failed"


@pytest.mark.asyncio
async def test_search_pagination_errors(admin_session, identity_factory):
    owner = identity_factory()
    async with _client() as client:
        await _login(client, owner)

        assert (
            await client.get("/api/v1/lots/", params={"page_size": 0})
        ).status_code == 422
        assert (
            await client.get("/api/v1/lots/", params={"page_size": 101})
        ).status_code == 422
        assert (
            await client.get("/api/v1/lots/", params={"cursor": "not-valid-cursor"})
        ).status_code == 400


@pytest.mark.asyncio
async def test_search_requires_authentication():
    async with _client() as client:
        assert (await client.get("/api/v1/lots/")).status_code == 401


@pytest.mark.asyncio
async def test_search_is_read_only_and_writes_audit(admin_session, identity_factory):
    owner = identity_factory()
    farm = _add_farm(admin_session, owner.organization_id, "Vùng chỉ đọc")
    lot = _add_lot(
        admin_session,
        owner.organization_id,
        farm.id,
        "Lô RO",
        "RO-01",
        date(2026, 5, 1),
    )

    async with audit_client() as client:
        await _login(client, owner)
        for params in [
            {},
            {"q": "RO-01"},
            {"farm_id": str(farm.id)},
            {"harvested_from": "2026-01-01", "harvested_to": "2026-12-31"},
        ]:
            response = await client.get("/api/v1/lots/", params=params)
            assert response.status_code == 200, response.text

    # Dữ liệu lô không bị thay đổi sau các lượt tra cứu
    with SessionLocal() as db:
        set_db_context(db, session_token_hash=owner.session_token_hash)
        unchanged = db.get(Lot, lot.id)
        assert unchanged is not None
        assert unchanged.quantity == Decimal("10.000")
        assert unchanged.remaining_quantity == Decimal("10.000")
        assert unchanged.status == "active"

    rows = _search_rows(admin_session, owner.user_id)
    assert len(rows) == 4
    assert all(r.outcome == "success" and r.status_code == 200 for r in rows)
