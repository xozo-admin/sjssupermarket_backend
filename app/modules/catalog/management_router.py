from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.catalog.management_schemas import (
    BrandCreate,
    BrandRead,
    NamedEntityCreate,
    NamedEntityRead,
    ProductCreate,
    ProductImportRequest,
    ProductImportResult,
    ProductList,
    ProductRead,
)
from app.modules.catalog.management_service import CatalogManagementService

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]
Kind = Literal["variations", "brands", "units", "taxes"]
FacetKind = Literal["categories", "variations", "brands", "units", "taxes"]


@router.get("/products/facets/{kind}", response_model=list[dict])
async def list_product_facets(kind: FacetKind, session: DbSession, search: str | None = None):
    return await CatalogManagementService(session).product_facets(kind, search)


@router.get("/{kind}", response_model=list[BrandRead] | list[NamedEntityRead])
async def list_entities(
    kind: Kind, session: DbSession, search: str | None = None, active: bool | None = None
):
    return await CatalogManagementService(session).list_entities(kind, search, active)


@router.post(
    "/{kind}", response_model=BrandRead | NamedEntityRead, status_code=status.HTTP_201_CREATED
)
async def create_entity(kind: Kind, payload: BrandCreate | NamedEntityCreate, session: DbSession):
    values = payload.model_dump()
    if kind != "brands":
        values = NamedEntityCreate.model_validate(values).model_dump()
    return await CatalogManagementService(session).create_entity(kind, values)


@router.patch("/{kind}/{entity_id}/toggle", response_model=BrandRead | NamedEntityRead)
async def toggle_entity(kind: Kind, entity_id: UUID, session: DbSession):
    return await CatalogManagementService(session).toggle_entity(kind, entity_id)


@router.put("/{kind}/{entity_id}", response_model=BrandRead | NamedEntityRead)
async def update_entity(
    kind: Kind, entity_id: UUID, payload: BrandCreate | NamedEntityCreate, session: DbSession
):
    values = payload.model_dump()
    if kind != "brands":
        values = NamedEntityCreate.model_validate(values).model_dump()
    return await CatalogManagementService(session).update_entity(kind, entity_id, values)


@router.delete("/{kind}/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity(kind: Kind, entity_id: UUID, session: DbSession) -> Response:
    await CatalogManagementService(session).delete_entity(kind, entity_id)
    return Response(status_code=204)


@router.get("/products/list", response_model=ProductList)
async def list_products(
    session: DbSession,
    search: str | None = None,
    brand: str | None = None,
    is_active: bool | None = None,
    stock_status: str | None = None,
    category_l1: str | None = None,
    category_l2: str | None = None,
    brands: str | None = None,
    min_rating: float | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    has_image: bool | None = None,
    sort: str = "popular",
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=0, le=10000),
) -> ProductList:
    items, total = await CatalogManagementService(session).list_products(
        search,
        brand,
        is_active,
        page,
        size,
        category_l1,
        category_l2,
        brands,
        min_rating,
        min_price,
        max_price,
        has_image,
        sort,
        stock_status,
    )
    pages = 1 if size == 0 else max(1, (total + size - 1) // size)
    return ProductList(items=items, total=total, page=page, size=size, pages=pages)


@router.post("/products/list", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, session: DbSession) -> ProductRead:
    return await CatalogManagementService(session).create_product(payload)


@router.post("/products/import", response_model=ProductImportResult)
async def import_products(payload: ProductImportRequest, session: DbSession) -> ProductImportResult:
    return await CatalogManagementService(session).import_products(payload.products)


@router.delete("/products/list/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: UUID, session: DbSession) -> Response:
    await CatalogManagementService(session).delete_product(product_id)
    return Response(status_code=204)


@router.get("/products/list/{product_id}", response_model=ProductRead)
async def get_product(product_id: UUID, session: DbSession) -> ProductRead:
    return await CatalogManagementService(session).get_product(product_id)


@router.put("/products/list/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: UUID, payload: ProductCreate, session: DbSession
) -> ProductRead:
    return await CatalogManagementService(session).update_product(product_id, payload)


@router.post("/products/list/{product_id}/image", response_model=ProductRead)
async def upload_product_image(
    product_id: UUID, session: DbSession, image: UploadFile = File(...)
) -> ProductRead:
    return await CatalogManagementService(session).upload_product_image(product_id, image)


@router.post("/brands/{brand_id}/image", response_model=BrandRead)
async def upload_brand_image(
    brand_id: UUID, session: DbSession, image: UploadFile = File(...)
) -> BrandRead:
    return await CatalogManagementService(session).upload_brand_image(brand_id, image)
