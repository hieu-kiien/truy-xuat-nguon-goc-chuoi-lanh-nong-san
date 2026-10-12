"""Bounded CSV validation and atomic imports using the runtime RLS session."""

import csv
from decimal import Decimal
from io import StringIO
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.farm import Farm
from app.models.identity import Organization
from app.models.product import Product
from app.schemas.farm import FarmFields
from app.schemas.product import ProductUnitValue

MAX_BYTES = 1024 * 1024
MAX_ROWS = 1000
HEADERS = {
    "products": ["name", "unit", "price", "quantity", "description"],
    "farms": ["organization_id", "name", "area_ha", "latitude", "longitude"],
}


class ProductRow(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    unit: ProductUnitValue
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    quantity: int = Field(ge=0, le=2147483647)
    description: str = Field(max_length=2000)

    @field_validator("name")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tên không được để trống.")
        return value.strip()


class FarmRow(FarmFields):
    organization_id: UUID


def invalid(errors: list[dict]) -> HTTPException:
    return HTTPException(
        422, {"message": "Không lưu dòng nào. Hãy sửa tệp CSV.", "errors": errors[:100]}
    )


def parse_csv(
    content: bytes, kind: Literal["products", "farms"]
) -> list[tuple[int, dict]]:
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Tệp CSV vượt giới hạn 1 MiB.")
    try:
        source = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise invalid(
            [{"line": 1, "column": "file", "message": "Tệp phải dùng UTF-8."}]
        ) from error
    reader = csv.reader(StringIO(source, newline=""), strict=True)
    rows, errors = [], []
    row_count = 0
    try:
        header = next(reader, [])
        if len(header) != len(set(header)) or set(header) != set(HEADERS[kind]):
            raise invalid(
                [
                    {
                        "line": 1,
                        "column": "header",
                        "message": "Cột phải gồm: " + ",".join(HEADERS[kind]),
                    }
                ]
            )
        model = ProductRow if kind == "products" else FarmRow
        while True:
            line = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                break
            row_count += 1
            if row_count > MAX_ROWS:
                raise HTTPException(413, "Tệp CSV vượt giới hạn 1000 dòng dữ liệu.")
            if len(row) != len(header):
                errors.append(
                    {"line": line, "column": "row", "message": "Số cột không khớp mẫu."}
                )
                continue
            nul_columns = [
                column
                for column, value in zip(header, row, strict=True)
                if "\x00" in value
            ]
            if nul_columns:
                errors.extend(
                    {
                        "line": line,
                        "column": column,
                        "message": "Ô dữ liệu chứa ký tự NUL không hợp lệ.",
                    }
                    for column in nul_columns
                )
                continue
            try:
                values = model.model_validate(
                    dict(zip(header, row, strict=True))
                ).model_dump()
                rows.append((line, values))
            except ValidationError as error:
                errors.extend(
                    {"line": line, "column": str(e["loc"][0]), "message": e["msg"]}
                    for e in error.errors(include_url=False, include_input=False)
                )
            if len(errors) >= 100:
                break
    except csv.Error as error:
        raise invalid(
            [{"line": reader.line_num, "column": "row", "message": "CSV không hợp lệ."}]
        ) from error
    if errors:
        raise invalid(errors)
    if not rows:
        raise invalid(
            [{"line": 2, "column": "row", "message": "Tệp không có dữ liệu."}]
        )
    return rows


def import_csv(
    db: Session,
    principal: Principal,
    content: bytes,
    kind: Literal["products", "farms"],
) -> int:
    if principal.role != "system_admin":
        raise HTTPException(403, "Chỉ quản trị hệ thống được nhập CSV.")
    rows = parse_csv(content, kind)
    errors = []
    if kind == "products":
        names = [values["name"].lower() for _, values in rows]
        existing = set(
            db.scalars(
                select(func.lower(Product.name)).where(
                    func.lower(Product.name).in_(names)
                )
            )
        )
        seen = set()
        for line, values in rows:
            key = values["name"].lower()
            if key in seen or key in existing:
                errors.append(
                    {
                        "line": line,
                        "column": "name",
                        "message": "Tên sản phẩm bị trùng.",
                    }
                )
            seen.add(key)
    else:
        org_ids = {values["organization_id"] for _, values in rows}
        allowed = set(
            db.scalars(
                select(Organization.id).where(
                    Organization.id.in_(org_ids),
                    Organization.is_active.is_(True),
                    Organization.organization_type.in_(["farm", "cooperative"]),
                )
            )
        )
        for line, values in rows:
            if values["organization_id"] not in allowed:
                errors.append(
                    {
                        "line": line,
                        "column": "organization_id",
                        "message": "Tổ chức phải là nông trại/HTX đang hoạt động.",
                    }
                )
    if errors:
        raise invalid(errors)
    model = Product if kind == "products" else Farm
    try:
        # Flush per row reports a concurrent DB constraint failure at its exact source.
        for _line, values in rows:
            db.add(model(**values))
            db.flush()
        db.commit()
    except IntegrityError as error:
        db.rollback()
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", "")
        if constraint in {"uq_product_name", "uq_products_name_ci"}:
            raise invalid(
                [
                    {
                        "line": _line,
                        "column": "name",
                        "message": "Tên sản phẩm đã tồn tại.",
                    }
                ]
            ) from error
        if constraint in {
            "fk_farms_organization_id_organizations",
            "farms_organization_id_fkey",
        }:
            raise invalid(
                [
                    {
                        "line": _line,
                        "column": "organization_id",
                        "message": "Tổ chức không còn tồn tại.",
                    }
                ]
            ) from error
        raise
    except Exception:
        db.rollback()
        raise
    return len(rows)


def eligible_import_organizations(db: Session) -> list[dict]:
    rows = db.execute(
        select(Organization.id, Organization.name)
        .where(
            Organization.is_active.is_(True),
            Organization.organization_type.in_(["farm", "cooperative"]),
        )
        .order_by(Organization.name)
    ).all()
    return [{"id": row.id, "name": row.name} for row in rows]
