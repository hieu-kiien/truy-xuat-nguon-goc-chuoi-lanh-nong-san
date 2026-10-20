"""Test suite for S-48, S-49, S-50: trang truy xuất công khai."""

from uuid import uuid4

import pytest

from app.core.auth import Principal
from app.core.public_fields import PUBLIC_TRACE_FIELDS
from app.services import event_service, public_trace_cache, public_trace_limiter
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login

lineage_products = fixtures.lineage_products


@pytest.fixture(autouse=True)
def _isolated_public_state():
    public_trace_cache.invalidate_all()
    public_trace_limiter.reset()
    yield
    public_trace_cache.invalidate_all()
    public_trace_limiter.reset()


def _holder_principal(identity) -> Principal:
    return Principal(
        user_id=identity.user_id,
        email=identity.email,
        full_name="Người giữ lô",
        organization_id=identity.organization_id,
        organization_name="Đối tác giữ lô",
        organization_type="cooperative",
        role="cooperative",
    )


@pytest.mark.asyncio
async def test_public_trace_returns_exactly_the_declared_allowlist(
    request, admin_session
):
    """S-48: phản hồi công khai khớp danh sách trường cho phép."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")
    holder = identities(role="cooperative", organization_type="cooperative")
    lot = add_lot(admin_session, holder, products[0])

    async with client() as api:
        response = await api.get(f"/api/v1/public/trace/{lot.lot_code}")

    assert response.status_code == 200, response.text
    trace = response.json()["trace"]
    assert set(trace.keys()) == set(PUBLIC_TRACE_FIELDS)


@pytest.mark.asyncio
async def test_public_trace_never_exposes_internal_fields(request, admin_session):
    """S-48: gọi thẳng API công khai cũng không lấy được trường nội bộ."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")
    holder = identities(role="cooperative", organization_type="cooperative")
    lot = add_lot(admin_session, holder, products[0])

    async with client() as api:
        response = await api.get(f"/api/v1/public/trace/{lot.lot_code}")

    assert response.status_code == 200, response.text
    body = response.text
    # Khối lượng, giá, tên đối tác và mọi định danh nội bộ phải vắng mặt.
    for internal_fragment in (
        "quantity",
        "price",
        "organization_id",
        "holder",
        "Đối tác giữ lô",
        str(lot.id),
        str(holder.organization_id),
    ):
        assert internal_fragment not in body, internal_fragment


@pytest.mark.asyncio
async def test_public_trace_shows_farm_name_and_organization_by_type(
    request, admin_session
):
    """S-48 NFR: vùng trồng hiện tên; tổ chức trung gian hiện theo loại."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")
    holder = identities(role="cooperative", organization_type="cooperative")
    lot = add_lot(admin_session, holder, products[0])

    async with client() as api:
        response = await api.get(f"/api/v1/public/trace/{lot.lot_code}")

    assert response.status_code == 200, response.text
    trace = response.json()["trace"]
    assert trace["farm_name"].startswith("lineage-")
    assert trace["origin_organization_type"] == "Hợp tác xã"


@pytest.mark.asyncio
async def test_public_trace_unknown_code_returns_404():
    """Mã không tồn tại trả 404 chung, không phân biệt được mã có hay không."""
    async with client() as api:
        response = await api.get("/api/v1/public/trace/ZZZZ9999")

    assert response.status_code == 404
    body = response.json()
    # Handler 404 của hệ thống trả thông điệp chung, không lộ khác biệt.
    assert body["detail"] == "Not Found"
    assert "trace" not in body


@pytest.mark.asyncio
async def test_recalled_lot_shows_red_warning_and_cache_invalidates(
    request, admin_session
):
    """S-49 + S-50 NFR: lô thu hồi hiện cảnh báo đỏ; cache bị vô hiệu ngay."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")
    holder = identities(role="cooperative", organization_type="cooperative")
    inspector = identities(role="inspector", organization_type="inspection")
    lot = add_lot(admin_session, holder, products[0])

    async with client() as api:
        # Lượt đầu: lô bình thường, phản hồi được cache.
        first = await api.get(f"/api/v1/public/trace/{lot.lot_code}")
        assert first.status_code == 200, first.text
        assert first.json()["warnings"] == []
        assert first.json()["trace"]["recall_active"] is False

        # Mở lệnh thu hồi (cache phải tự hủy, không chờ 60 giây).
        await login(api, inspector)
        recall = await api.post(
            "/api/v1/recalls/",
            json={
                "lot_id": str(lot.id),
                "reason": "Phát hiện nhiễm khuẩn vượt ngưỡng an toàn thực phẩm.",
            },
        )
        assert recall.status_code == 201, recall.text

    async with client() as api:
        second = await api.get(f"/api/v1/public/trace/{lot.lot_code}")

    assert second.status_code == 200, second.text
    payload = second.json()
    assert payload["trace"]["recall_active"] is True
    assert len(payload["warnings"]) == 1
    warning = payload["warnings"][0]
    assert warning["code"] == "recall"
    assert warning["level"] == "danger"
    assert "thu hồi" in warning["message"].lower()


@pytest.mark.asyncio
async def test_cold_chain_violation_note_hides_measurements(request, admin_session):
    """S-49: vi phạm chuỗi lạnh hiện ghi chú trung tính, không lộ số đo."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")
    holder = identities(role="cooperative", organization_type="cooperative")
    lot = add_lot(admin_session, holder, products[0])

    event_service.append_event(
        admin_session,
        _holder_principal(holder),
        lot.id,
        event_type="cold_chain_violation",
        payload={"peak_temperature_celsius": 15.5, "duration_minutes": 42},
    )
    admin_session.commit()

    async with client() as api:
        response = await api.get(f"/api/v1/public/trace/{lot.lot_code}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["trace"]["cold_chain_violation"] is True
    codes = [warning["code"] for warning in payload["warnings"]]
    assert codes == ["cold_chain"]
    note = payload["warnings"][0]
    assert note["level"] == "note"
    # Không lộ số đo nhiệt độ hay thời lượng.
    assert "15.5" not in response.text
    assert "peak_temperature" not in response.text
    assert "duration_minutes" not in response.text


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_30_distinct_codes_in_a_minute():
    """S-50: quá 30 mã lô khác nhau mỗi phút bị chặn tạm; mã sai cũng bị đếm."""
    async with client() as api:
        for index in range(30):
            code = f"NOPE{index:04d}"
            response = await api.get(f"/api/v1/public/trace/{code}")
            assert response.status_code == 404, response.text

        blocked = await api.get("/api/v1/public/trace/NOPE9999")

    assert blocked.status_code == 429
    assert blocked.headers.get("retry-after")
    assert "quá nhiều" in blocked.json()["detail"].lower()


@pytest.mark.asyncio
async def test_repeated_same_code_does_not_trip_the_rate_limit():
    """S-50: giới hạn đếm MÃ KHÁC NHAU, tra cứu lại mã cũ không bị chặn."""
    async with client() as api:
        for _ in range(5):
            response = await api.get("/api/v1/public/trace/SAME0001")
            assert response.status_code == 404
        final = await api.get("/api/v1/public/trace/SAME0001")

    assert final.status_code == 404


def test_public_cache_stores_only_projection():
    """Cache chỉ giữ phản hồi công khai đã dựng (không giữ dữ liệu nội bộ)."""
    payload = {"trace": {"lot_code": "ABC12345"}, "warnings": []}
    key = uuid4().hex
    public_trace_cache.put(key, payload)
    try:
        assert public_trace_cache.get(key) == payload
    finally:
        public_trace_cache.invalidate(key)
    assert public_trace_cache.get(key) is None
