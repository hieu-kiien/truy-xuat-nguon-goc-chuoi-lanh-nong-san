from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    administration,
    cold_chain,
    farms,
    lots,
    products,
    shipments,
)
from app.core.authorization import enforce_route_permission

# `api_router` is the single protected business surface. `enforce_route_permission`
# denies (403) any route whose endpoint is missing `@require_permission`, so a
# developer cannot accidentally expose a business route by including it here
# without declaring its permission.
api_router = APIRouter(dependencies=[Depends(enforce_route_permission)])

api_router.include_router(farms.router, prefix="/farms", tags=["farms"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(lots.router, prefix="/lots", tags=["lots"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["shipments"])
api_router.include_router(cold_chain.router, tags=["cold chain"])
api_router.include_router(administration.router, tags=["administration"])
