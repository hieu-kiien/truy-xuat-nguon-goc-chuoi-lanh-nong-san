from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.catalog import Product
from app.schemas.traceability import Page, ProductCreate, ProductRead

router = APIRouter()


@router.get("/", response_model=Page[ProductRead])
@require_permission("products:read")
def list_products(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> Page[ProductRead]:
    base = tenant_select(Product, principal)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    products = db.scalars(
        base.order_by(Product.created_at.desc(), Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(products), page=page, page_size=page_size, total=total)


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
@require_permission("products:write")
def create_product(
    payload: ProductCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    product = Product(organization_id=principal.organization_id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductRead)
@require_permission("products:read")
def get_product(
    product_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    return get_tenant_record(db, Product, product_id, principal)
