from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot

lineage = fixtures.lineage
lineage_products = fixtures.lineage_products


@pytest.mark.parametrize("action", ["accept", "reject"])
def test_resolving_same_handover_concurrently_returns_conflict(
    lineage, admin_session, action
):
    receiver, products, identities = lineage
    sender = identities()
    lot = add_lot(admin_session, sender, products[0])
    with TestClient(app, base_url="https://testserver") as api:
        assert (
            api.post(
                "/api/v1/auth/login",
                json={"email": sender.email, "password": sender.password},
            ).status_code
            == 200
        )
        handover_id = api.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(lot.id),
                "to_organization_id": str(receiver.organization_id),
            },
        ).json()["id"]
    barrier = Barrier(2)

    def resolve():
        with TestClient(
            app, base_url="https://testserver", raise_server_exceptions=False
        ) as api:
            assert (
                api.post(
                    "/api/v1/auth/login",
                    json={"email": receiver.email, "password": receiver.password},
                ).status_code
                == 200
            )
            barrier.wait(timeout=10)
            return api.post(
                f"/api/v1/handovers/{handover_id}/{action}",
                json={"reason": "Independent rejection"}
                if action == "reject"
                else None,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: resolve(), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 409], [
        response.text for response in responses
    ]
