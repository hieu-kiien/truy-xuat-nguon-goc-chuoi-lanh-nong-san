"""N3-72: hồ sơ truy xuất PDF kèm kết quả kiểm toàn vẹn của một lô."""

from io import BytesIO
from uuid import uuid4

import pytest
from pypdf import PdfReader
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import lot_report_service
from tests import test_event_integrity as integrity
from tests.lineage_helpers import client, login


def _pdf_text(payload: bytes) -> str:
    reader = PdfReader(BytesIO(payload))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


@pytest.mark.asyncio
async def test_report_pdf_contains_lot_events_and_valid_integrity(
    admin_session: Session, identity_factory
):
    owner = identity_factory()
    farm, product, lot, principal = integrity._create_lot_records(
        admin_session, owner, uuid4().hex[:8]
    )
    try:
        integrity._append_chain(admin_session, principal, lot.id, 3)

        async with client() as api:
            await login(api, owner)
            response = await api.get(f"/api/v1/lots/{lot.id}/report.pdf")

        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/pdf")
        assert "attachment;" in response.headers["content-disposition"]
        assert lot.lot_code in response.headers["content-disposition"]
        assert response.headers["cache-control"] == "no-store"
        assert response.content.startswith(b"%PDF-")

        content = _pdf_text(response.content)
        assert lot.lot_code in content
        assert "HỒ SƠ TRUY XUẤT NGUỒN GỐC" in content
        assert "Chuỗi sự kiện hợp lệ" in content
        assert "Đã kiểm tra 3 sự kiện" in content
        # Mỗi sự kiện trong chuỗi đều có mặt trong bảng lịch sử.
        assert content.count("integrity_test") >= 3
    finally:
        integrity._cleanup_lot_records(admin_session, farm, product, [lot.id])


@pytest.mark.asyncio
async def test_report_pdf_reports_tampered_chain(
    admin_session: Session, identity_factory
):
    owner = identity_factory()
    farm, product, lot, principal = integrity._create_lot_records(
        admin_session, owner, uuid4().hex[:8]
    )
    try:
        integrity._append_chain(admin_session, principal, lot.id, 3)
        with admin_session.begin_nested():
            admin_session.execute(text("ALTER TABLE events DISABLE TRIGGER USER"))
            admin_session.execute(
                text(
                    "UPDATE events SET payload = CAST(:payload AS jsonb) "
                    "WHERE lot_id = :lot_id AND sequence_number = 2"
                ),
                {"payload": '{"value":999}', "lot_id": lot.id},
            )
            admin_session.execute(text("ALTER TABLE events ENABLE TRIGGER USER"))
        admin_session.commit()
        admin_session.expire_all()

        async with client() as api:
            await login(api, owner)
            response = await api.get(f"/api/v1/lots/{lot.id}/report.pdf")

        assert response.status_code == 200, response.text
        content = _pdf_text(response.content)
        assert "Phát hiện sai lệch chuỗi sự kiện" in content
        assert "Sai lệch đầu tiên tại sự kiện 2" in content
        assert "Nội dung sự kiện không khớp mã băm" in content
        assert "Chuỗi sự kiện hợp lệ" not in content
    finally:
        integrity._cleanup_lot_records(admin_session, farm, product, [lot.id])


@pytest.mark.asyncio
async def test_report_pdf_requires_access_to_the_lot(
    admin_session: Session, identity_factory
):
    owner = identity_factory()
    stranger = identity_factory()
    farm, product, lot, principal = integrity._create_lot_records(
        admin_session, owner, uuid4().hex[:8]
    )
    try:
        integrity._append_chain(admin_session, principal, lot.id, 1)

        async with client() as api:
            await login(api, stranger)
            response = await api.get(f"/api/v1/lots/{lot.id}/report.pdf")

        assert response.status_code == 403, response.text
        assert response.headers["content-type"].startswith("application/json")
    finally:
        integrity._cleanup_lot_records(admin_session, farm, product, [lot.id])


@pytest.mark.asyncio
async def test_report_pdf_hides_lots_from_other_organizations(
    admin_session: Session, identity_factory
):
    """Không lộ sự tồn tại của lô: tổ chức khác nhận 403, không phải 404."""
    owner = identity_factory()
    stranger = identity_factory()
    farm, product, lot, principal = integrity._create_lot_records(
        admin_session, owner, uuid4().hex[:8]
    )
    try:
        integrity._append_chain(admin_session, principal, lot.id, 1)

        async with client() as api:
            await login(api, stranger)
            response = await api.get(f"/api/v1/lots/{lot.id}/report.pdf")
            unknown = await api.get(f"/api/v1/lots/{uuid4()}/report.pdf")

        assert response.status_code == 403, response.text
        assert response.headers["content-type"].startswith("application/json")
        assert unknown.status_code == 403, unknown.text
    finally:
        integrity._cleanup_lot_records(admin_session, farm, product, [lot.id])


def test_report_file_name_keeps_only_safe_characters():
    assert (
        lot_report_service.report_file_name("V1A2B3C4")
        == "ho-so-truy-xuat-V1A2B3C4.pdf"
    )
    assert (
        lot_report_service.report_file_name('A B/../C"') == "ho-so-truy-xuat-A-B-C.pdf"
    )
    assert lot_report_service.report_file_name("***") == "ho-so-truy-xuat-lo.pdf"
