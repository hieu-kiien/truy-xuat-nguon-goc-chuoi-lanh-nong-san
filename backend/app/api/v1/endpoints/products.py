from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead
from app.services import product_service

router = APIRouter()


@router.get("/", response_model=list[ProductRead])
@require_permission("products:read")
def list_products(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Product]:
    return product_service.list_products(db)


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
@require_permission("products:create")
def create_product(
    payload: ProductCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    return product_service.create_product(db, payload)
