from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.catalog.category_repository import CategoryRepository
from app.modules.catalog.category_schemas import (
    CategoryCreate,
    CategoryList,
    CategoryRead,
    CategoryUpdate,
)
from app.modules.catalog.category_service import CategoryService

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


def service(session: AsyncSession) -> CategoryService:
    return CategoryService(CategoryRepository(session))


@router.get("", response_model=CategoryList)
async def list_categories(
    session: DbSession,
    search: str | None = Query(default=None, max_length=150),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=500),
) -> CategoryList:
    items, total = await service(session).list(search, page, size)
    return CategoryList(items=items, total=total, page=page, size=size)


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(category_id: UUID, session: DbSession) -> CategoryRead:
    return await service(session).get(category_id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoryCreate, session: DbSession) -> CategoryRead:
    category = await service(session).create(payload)
    await session.commit()
    return category


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: UUID, payload: CategoryUpdate, session: DbSession
) -> CategoryRead:
    category = await service(session).update(category_id, payload)
    await session.commit()
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: UUID, session: DbSession) -> Response:
    await service(session).delete(category_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{category_id}/image", response_model=CategoryRead)
async def upload_category_image(
    category_id: UUID, session: DbSession, image: UploadFile = File(...)
) -> CategoryRead:
    category = await service(session).upload_image(category_id, image)
    await session.commit()
    return category
