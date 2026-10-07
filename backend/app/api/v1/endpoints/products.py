from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authorization import require_permission
from app.core.database import get_db
from app.core.tenancy import shared_select
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(tags=["products"])
PRODUCT_NAME_CONFLICT = "Tên sản phẩm đã tồn tại. Vui lòng chọn tên khác."


def _commit_product(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint_name = getattr(
            getattr(exc.orig, "diag", None), "constraint_name", None
        )
        if constraint_name == "uq_product_name":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=PRODUCT_NAME_CONFLICT,
            ) from exc
        raise


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
@require_permission("products:write")
def create_product(
    product_in: ProductCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    product = Product(**product_in.model_dump())
    db.add(product)

    _commit_product(db)
    db.refresh(product)
    return product


@router.get("/", response_model=list[ProductRead])
@require_permission("products:read")
def list_products(
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
) -> list[Product]:
    return list(db.scalars(shared_select(Product).offset(skip).limit(limit)).all())


@router.get("/{product_id}", response_model=ProductRead)
@require_permission("products:read")
def get_product(product_id: UUID, db: Annotated[Session, Depends(get_db)]) -> Product:
    product = db.scalar(shared_select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.put("/{product_id}", response_model=ProductRead)
@require_permission("products:write")
def update_product(
    product_id: UUID,
    product_in: ProductUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    product = db.scalar(shared_select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    _commit_product(db)
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("products:write")
def delete_product(product_id: UUID, db: Annotated[Session, Depends(get_db)]) -> None:
    product = db.scalar(shared_select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    db.delete(product)
    db.commit()
