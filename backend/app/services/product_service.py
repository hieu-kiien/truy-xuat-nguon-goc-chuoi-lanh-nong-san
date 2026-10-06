from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate


def list_products(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).order_by(func.lower(Product.name))).all())


def create_product(db: Session, product_in: ProductCreate) -> Product:
    existing_id = db.scalar(
        select(Product.id).where(func.lower(Product.name) == product_in.name.lower())
    )
    if existing_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sản phẩm đã có trong danh mục.",
        )

    product = Product(name=product_in.name, unit=product_in.unit)
    db.add(product)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        diagnostic = getattr(error.orig, "diag", None)
        if getattr(diagnostic, "constraint_name", None) == "uq_products_name_ci":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sản phẩm đã có trong danh mục.",
            ) from error
        raise

    db.refresh(product)
    return product
