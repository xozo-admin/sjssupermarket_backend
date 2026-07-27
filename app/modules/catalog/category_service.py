import re
from uuid import UUID
from fastapi import UploadFile

from app.exceptions import AppError
from app.integrations.storage.r2 import R2Storage
from app.modules.catalog.category_model import Category
from app.modules.catalog.category_repository import CategoryRepository
from app.modules.catalog.category_schemas import CategoryCreate, CategoryRead, CategoryUpdate


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "category"


def to_read(category: Category, product_count: int = 0) -> CategoryRead:
    data = category.to_dict()
    data["parent_name"] = category.parent.name if category.parent else None
    data["product_count"] = product_count
    return CategoryRead.model_validate(data)


class CategoryService:
    def __init__(self, repository: CategoryRepository) -> None:
        self.repository = repository

    async def list(
        self, search: str | None, page: int, size: int
    ) -> tuple[list[CategoryRead], int]:
        categories, total = await self.repository.list(search, page, size)
        l1_counts, l2_counts = await self.repository.product_counts()
        return [
            to_read(
                category,
                (l2_counts if category.parent_id else l1_counts).get(category.name.casefold(), 0),
            )
            for category in categories
        ], total

    async def get(self, category_id: UUID) -> CategoryRead:
        category = await self.repository.get(category_id)
        if not category:
            raise AppError("Category not found", 404)
        return to_read(category)

    async def create(self, payload: CategoryCreate) -> CategoryRead:
        if await self.repository.get_by_name(payload.name):
            raise AppError("A category with this name already exists", 409)
        if payload.parent_id:
            parent = await self.repository.get(payload.parent_id)
            if not parent:
                raise AppError("Main category not found", 422)
            if parent.parent_id:
                raise AppError("A subcategory can only belong to a main category", 422)
        category = Category(**payload.model_dump(), slug=slugify(payload.name))
        await self.repository.add(category)
        category = await self.repository.get(category.id)
        return to_read(category)  # type: ignore[arg-type]

    async def update(self, category_id: UUID, payload: CategoryUpdate) -> CategoryRead:
        category = await self.repository.get(category_id)
        if not category:
            raise AppError("Category not found", 404)
        values = payload.model_dump(exclude_unset=True)
        if values.get("parent_id") == category_id:
            raise AppError("A category cannot be its own base category", 422)
        if values.get("parent_id"):
            parent = await self.repository.get(values["parent_id"])
            if not parent or parent.parent_id:
                raise AppError("A subcategory can only belong to a main category", 422)
        if "name" in values:
            duplicate = await self.repository.get_by_name(values["name"])
            if duplicate and duplicate.id != category.id:
                raise AppError("A category with this name already exists", 409)
            values["slug"] = slugify(values["name"])
        for key, value in values.items():
            setattr(category, key, value)
        await self.repository.session.flush()
        category = await self.repository.get(category.id)
        return to_read(category)  # type: ignore[arg-type]

    async def delete(self, category_id: UUID) -> None:
        category = await self.repository.get(category_id)
        if not category:
            raise AppError("Category not found", 404)
        child_count = await self.repository.count_children(category_id)
        if child_count:
            label = "subcategory" if child_count == 1 else "subcategories"
            raise AppError(
                f"Cannot delete this main category because it contains {child_count} {label}. "
                "Delete or move the subcategories first.",
                409,
            )
        await self.repository.delete(category)

    async def upload_image(self, category_id: UUID, upload: UploadFile) -> CategoryRead:
        category = await self.repository.get(category_id)
        if not category:
            raise AppError("Category not found", 404)
        storage = R2Storage()
        content, extension = await storage.read_image(upload)
        filename = storage.safe_filename(category.name, extension)
        key = f"categories/{category.id}/{filename}"
        await storage.put(key, content, upload.content_type or "image/webp")
        category.thumbnail_url = storage.public_url(key)
        await self.repository.session.flush()
        refreshed = await self.repository.get(category.id)
        if not refreshed:
            raise AppError("Category not found after image upload", 404)
        return to_read(refreshed)
