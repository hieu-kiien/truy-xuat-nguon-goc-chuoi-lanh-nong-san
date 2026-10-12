import asyncio
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, event, select

from app.core.database import engine
from app.models.product import Product
from app.services.csv_import_service import MAX_BYTES, parse_csv
from tests.lineage_helpers import client, login


@pytest.mark.parametrize(
    "body,column",
    [
        (
            b"name,unit,price,quantity,description\nvalid,kg,1,2,\nbad,kg,NaN,2,\n",
            "price",
        ),
        (
            b"name,unit,price,quantity,description\nvalid,kg,1,2,\nbad,kg,1,1.5,\n",
            "quantity",
        ),
        (
            b"name,unit,price,quantity,description\nvalid,kg,1,2,\nbad,liter,1,2,\n",
            "unit",
        ),
        (
            b"name,unit,price,quantity,description\nvalid,kg,1,2,\nbad\x00name,kg,1,2,\n",
            "name",
        ),
        (
            b"name,unit,price,quantity,description\nvalid,kg,1,2,\nbad,kg,1,2,bad\x00text\n",
            "description",
        ),
    ],
)
def test_csv_reports_physical_line_and_column(body, column):
    with pytest.raises(HTTPException) as exc:
        parse_csv(body, "products")
    assert exc.value.status_code == 422
    assert exc.value.detail["errors"][0]["line"] == 3
    assert exc.value.detail["errors"][0]["column"] == column


@pytest.mark.parametrize(
    "body",
    [
        b"name,name\nx,y\n",
        b"name,unit\nx,kg\n",
        b"name,unit,price,quantity,description\n",
        b"\xff",
    ],
)
def test_csv_rejects_bad_template_or_encoding(body):
    with pytest.raises(HTTPException) as exc:
        parse_csv(body, "products")
    assert exc.value.status_code == 422


def test_csv_enforces_size_limit():
    with pytest.raises(HTTPException) as exc:
        parse_csv(b"x" * (MAX_BYTES + 1), "products")
    assert exc.value.status_code == 413


def test_csv_quoted_multiline_and_row_limit():
    body = 'name,unit,price,quantity,description\n"Rau, sạch",kg,1.20,2,"hai\ndòng"\n'
    parsed = parse_csv(body.encode("utf-8-sig"), "products")
    assert parsed[0][0] == 2
    assert parsed[0][1]["name"] == "Rau, sạch"
    assert parsed[0][1]["description"] == "hai\ndòng"
    with pytest.raises(HTTPException) as exc:
        parse_csv(
            ("name,unit,price,quantity,description\n" + "x,kg,1,1,\n" * 1001).encode(),
            "products",
        )
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_import_products_all_or_none_duplicates_and_permission(
    identity_factory, admin_session
):
    admin = identity_factory(role="system_admin", organization_type="administration")
    grower = identity_factory()
    prefix = uuid4().hex
    async with client() as api:
        await login(api, grower)
        denied = await api.post(
            "/api/v1/imports/products",
            content=b"ignored",
            headers={"Content-Type": "text/csv"},
        )
        assert denied.status_code == 403
        await login(api, admin)
        header = "name,unit,price,quantity,description\n"
        good = f"{prefix}A,kg,1.20,2,test\n"
        bad = f"{prefix}B,kg,-1,2,test\n"
        response = await api.post(
            "/api/v1/imports/products",
            content=(header + good + bad).encode(),
            headers={"Content-Type": "text/csv"},
        )
        assert response.status_code == 422, response.text
        assert not admin_session.scalar(
            select(Product.id).where(Product.name == prefix + "A")
        )
        try:
            valid = await api.post(
                "/api/v1/imports/products",
                content=(header + good).encode(),
                headers={"Content-Type": "text/csv"},
            )
            assert valid.status_code == 201, valid.text
            assert valid.json()["created"] == 1
            duplicate = await api.post(
                "/api/v1/imports/products",
                content=(header + bad.replace("-1", "1") + good).encode(),
                headers={"Content-Type": "text/csv"},
            )
            assert duplicate.status_code == 422, duplicate.text
            assert duplicate.json()["detail"]["errors"][0]["column"] == "name"
            assert not admin_session.scalar(
                select(Product.id).where(Product.name == prefix + "B")
            )
        finally:
            admin_session.execute(
                delete(Product).where(Product.name.in_([prefix + "A", prefix + "B"]))
            )
            admin_session.commit()


@pytest.mark.asyncio
async def test_import_farms_targets_org_atomic_and_invalid_uuid(
    identity_factory, admin_session
):
    from app.models.farm import Farm

    admin = identity_factory(role="system_admin", organization_type="administration")
    target = identity_factory(
        role="organization_admin", organization_type="cooperative"
    )
    prefix = uuid4().hex
    header = "organization_id,name,area_ha,latitude,longitude\n"
    good = f"{target.organization_id},{prefix},1.5,10,106\n"
    async with client() as api:
        await login(api, admin)
        organizations = await api.get("/api/v1/imports/organizations")
        assert organizations.status_code == 200
        assert str(target.organization_id) in {o["id"] for o in organizations.json()}
        assert str(admin.organization_id) not in {o["id"] for o in organizations.json()}
        invalid = await api.post(
            "/api/v1/imports/farms",
            content=(header + good + "bad,x,1,10,106\n").encode(),
            headers={"Content-Type": "text/csv"},
        )
        assert invalid.status_code == 422, invalid.text
        assert invalid.json()["detail"]["errors"][0]["column"] == "organization_id"
        assert not admin_session.scalar(select(Farm.id).where(Farm.name == prefix))
        valid = await api.post(
            "/api/v1/imports/farms",
            content=(header + good).encode(),
            headers={"Content-Type": "text/csv"},
        )
        assert valid.status_code == 201, valid.text
        farm = admin_session.scalar(select(Farm).where(Farm.name == prefix))
        assert farm.organization_id == target.organization_id


@pytest.mark.asyncio
async def test_concurrent_csv_conflict_rolls_back_earlier_rows(
    identity_factory, admin_session
):
    admin = identity_factory(role="system_admin", organization_type="administration")
    prefix = uuid4().hex
    barrier = Barrier(2)

    def synchronize(connection, cursor, statement, parameters, context, executemany):
        if "SELECT lower(products.name)" in statement:
            barrier.wait(timeout=10)

    async with client() as api:
        await login(api, admin)
        event.listen(engine, "before_cursor_execute", synchronize)
        try:
            header = "name,unit,price,quantity,description\n"
            bodies = [
                header + f"{prefix}{index},kg,1,1,\n{prefix}shared,kg,1,1,\n"
                for index in range(2)
            ]
            responses = await asyncio.gather(
                *(
                    api.post(
                        "/api/v1/imports/products",
                        content=body.encode(),
                        headers={"Content-Type": "text/csv"},
                    )
                    for body in bodies
                )
            )
            assert sorted(r.status_code for r in responses) == [201, 422], [
                r.text for r in responses
            ]
            failed = next(r for r in responses if r.status_code == 422)
            assert failed.json()["detail"]["errors"][0]["line"] == 3
            names = set(
                admin_session.scalars(
                    select(Product.name).where(Product.name.like(prefix + "%"))
                )
            )
            assert len(names) == 2
            assert prefix + "shared" in names
            assert len(names & {prefix + "0", prefix + "1"}) == 1
        finally:
            event.remove(engine, "before_cursor_execute", synchronize)
            admin_session.execute(
                delete(Product).where(Product.name.like(prefix + "%"))
            )
            admin_session.commit()


@pytest.mark.asyncio
async def test_csv_deleted_target_constraint_reports_column_and_rolls_back(
    identity_factory, admin_session, admin_engine
):
    from app.models.farm import Farm
    from app.models.identity import Organization

    admin = identity_factory(role="system_admin", organization_type="administration")
    prefix = uuid4().hex
    orgs = [
        Organization(
            name=f"csv-{prefix}-{index}",
            organization_type="cooperative",
            is_active=True,
        )
        for index in range(2)
    ]
    admin_session.add_all(orgs)
    admin_session.commit()
    ids = [o.id for o in orgs]

    def delete_target(connection, cursor, statement, parameters, context, executemany):
        if (
            statement.startswith("INSERT INTO farms")
            and parameters.get("organization_id") == ids[1]
        ):
            with admin_engine.begin() as other:
                other.execute(delete(Organization).where(Organization.id == ids[1]))

    async with client() as api:
        await login(api, admin)
        event.listen(engine, "before_cursor_execute", delete_target)
        try:
            body = "organization_id,name,area_ha,latitude,longitude\n" + "".join(
                f"{org_id},{prefix}-{index},1,10,106\n"
                for index, org_id in enumerate(ids)
            )
            response = await api.post(
                "/api/v1/imports/farms",
                content=body.encode(),
                headers={"Content-Type": "text/csv"},
            )
            assert response.status_code == 422, response.text
            assert response.json()["detail"]["errors"][0]["line"] == 3
            assert response.json()["detail"]["errors"][0]["column"] == "organization_id"
            assert not admin_session.scalar(
                select(Farm.id).where(Farm.name.like(prefix + "%"))
            )
        finally:
            event.remove(engine, "before_cursor_execute", delete_target)
            admin_session.execute(delete(Farm).where(Farm.name.like(prefix + "%")))
            admin_session.execute(delete(Organization).where(Organization.id.in_(ids)))
            admin_session.commit()
