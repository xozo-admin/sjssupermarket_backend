from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.category_model import Category
from app.modules.catalog.management_models import Product


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, search: str | None, page: int, size: int) -> tuple[list[Category], int]:
        filters = []
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(or_(Category.name.ilike(pattern), Category.description.ilike(pattern)))
        query = select(Category).options(selectinload(Category.parent)).where(*filters)
        count_query = select(func.count(Category.id)).where(*filters)
        total = await self.session.scalar(count_query) or 0
        result = await self.session.scalars(
            query.order_by(Category.priority.desc(), Category.name)
            .offset((page - 1) * size)
            .limit(size)
        )
        return list(result), total

    async def get(self, category_id: UUID) -> Category | None:
        return await self.session.scalar(
            select(Category)
            .options(selectinload(Category.parent))
            .where(Category.id == category_id)
        )

    async def get_by_name(self, name: str) -> Category | None:
        return await self.session.scalar(
            select(Category).where(func.lower(Category.name) == name.lower())
        )

    async def add(self, category: Category) -> Category:
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def delete(self, category: Category) -> None:
        await self.session.delete(category)

    async def count_children(self, category_id: UUID) -> int:
        return (
            await self.session.scalar(
                select(func.count(Category.id)).where(Category.parent_id == category_id)
            )
            or 0
        )

    async def product_counts(self) -> tuple[dict[str, int], dict[str, int]]:
        l1_rows = await self.session.execute(
            select(Product.category_l1, func.count(Product.id))
            .where(Product.archived.is_(False))
            .group_by(Product.category_l1)
        )
        l2_rows = await self.session.execute(
            select(Product.category_l2, func.count(Product.id))
            .where(Product.archived.is_(False), Product.category_l2.is_not(None))
            .group_by(Product.category_l2)
        )
        return (
            {name.casefold(): count for name, count in l1_rows if name},
            {name.casefold(): count for name, count in l2_rows if name},
        )
