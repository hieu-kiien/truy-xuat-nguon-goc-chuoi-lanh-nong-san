"""Cache topology only; prove expiry, fresh quantities and caller isolation."""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import event

from app.core.auth import Principal
from app.core.database import SessionLocal, set_db_context
from app.services import ancestor_cache
from app.services.traversal_service import get_lineage
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot

lineage = fixtures.lineage
lineage_products = fixtures.lineage_products


def test_topology_cache_skips_recursive_discovery_but_refreshes_stock(
    lineage, admin_session, monkeypatch
):
    owner, products, identities = lineage
    lot = add_lot(admin_session, owner, products[0])
    now = [100.0]
    monkeypatch.setattr(ancestor_cache, "monotonic", lambda: now[0])
    principal = Principal(
        owner.user_id,
        owner.email,
        "Test",
        owner.organization_id,
        "Test",
        "cooperative",
        "cooperative",
    )

    def read(identity, actor):
        with SessionLocal() as db:
            set_db_context(db, session_token_hash=identity.session_token_hash)
            statements = []
            event.listen(
                db.connection(),
                "before_cursor_execute",
                lambda conn, cursor, statement, parameters, context, many: (
                    statements.append(statement)
                ),
            )
            result = get_lineage(db, actor, lot.id, "ancestors")
            return result, statements

    _, first = read(owner, principal)
    assert any("WITH RECURSIVE" in statement for statement in first)
    lot.remaining_quantity = Decimal("39")
    admin_session.commit()
    result, cached = read(owner, principal)
    assert not any("WITH RECURSIVE" in statement for statement in cached)
    assert result["nodes"][0]["remaining_quantity"] == Decimal("39")
    other = identities(role="cooperative", organization_type="cooperative")
    other_principal = Principal(
        other.user_id,
        other.email,
        "Other",
        other.organization_id,
        "Other",
        "cooperative",
        "cooperative",
    )
    try:
        read(other, other_principal)
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError(
            "Cached topology must not grant another organization access."
        )
    now[0] += 60
    _, expired = read(owner, principal)
    assert any("WITH RECURSIVE" in statement for statement in expired)
