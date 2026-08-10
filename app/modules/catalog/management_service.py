import re
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import String, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.exceptions import AppError
from app.integrations.storage.r2 import R2Storage
from app.modules.catalog.category_model import Category
from app.modules.catalog.management_models import Brand, Product, Tax, Unit, Variation
from app.modules.catalog.management_schemas import ProductCreate, ProductImportResult, ProductRead
from app.modules.orders.models import OrderItem

Entity = TypeVar("Entity", Brand, Tax, Unit, Variation)
ENTITY_MODELS = {"variations": Variation, "brands": Brand, "units": Unit, "taxes": Tax}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "product"


class CatalogManagementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_entities(self, kind: str, search: str | None, active: bool | None) -> list[Any]:
        model = ENTITY_MODELS[kind]
        query = select(model)
        if search:
            query = query.where(model.name.ilike(f"%{search.strip()}%"))
        if active is not None:
            query = query.where(model.active == active)
        return list(await self.session.scalars(query.order_by(model.name)))

    async def create_entity(self, kind: str, values: dict[str, Any]) -> Any:
        model = ENTITY_MODELS[kind]
        duplicate = await self.session.scalar(
            select(model).where(func.lower(model.name) == values["name"].lower())
        )
        if duplicate:
            raise AppError(f"{kind[:-1].title()} already exists", 409)
        entity = model(**values)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def toggle_entity(self, kind: str, entity_id: UUID) -> Any:
        model = ENTITY_MODELS[kind]
        entity = await self.session.get(model, entity_id)
        if not entity:
            raise AppError("Item not found", 404)
        entity.active = not entity.active
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update_entity(self, kind: str, entity_id: UUID, values: dict[str, Any]) -> Any:
        model = ENTITY_MODELS[kind]
        entity = await self.session.get(model, entity_id)
        if not entity:
            raise AppError("Item not found", 404)
        duplicate = await self.session.scalar(
            select(model).where(
                func.lower(model.name) == values["name"].lower(), model.id != entity_id
            )
        )
        if duplicate:
            raise AppError(f"{kind[:-1].title()} already exists", 409)
        for key, value in values.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete_entity(self, kind: str, entity_id: UUID) -> None:
        model = ENTITY_MODELS[kind]
        entity = await self.session.get(model, entity_id)
        if not entity:
            raise AppError("Item not found", 404)
        await self.session.delete(entity)
        await self.session.commit()

    async def list_products(
        self,
        search: str | None,
        brand: str | None,
        is_active: bool | None,
        page: int,
        size: int,
        category_l1: str | None = None,
        category_l2: str | None = None,
        brands: str | None = None,
        min_rating: float | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        has_image: bool | None = None,
        sort: str = "popular",
        stock_status: str | None = None,
    ) -> tuple[list[ProductRead], int]:
        filters = [Product.archived.is_(False)]
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    Product.name.ilike(pattern),
                    Product.platform_product_id.ilike(pattern),
                    Product.barcode.ilike(pattern),
                )
            )
        if brand:
            filters.append(Product.brand == brand)
        if is_active is not None:
            filters.append(Product.is_active == is_active)
        if stock_status:
            filters.append(Product.stock_status == stock_status)
        if category_l1:
            filters.append(Product.category_l1 == category_l1)
        if category_l2:
            filters.append(Product.category_l2 == category_l2)
        if brands:
            filters.append(Product.brand.in_([item for item in brands.split("|") if item]))
        if min_rating is not None:
            filters.append(Product.rating >= min_rating)
        if min_price is not None:
            filters.append(Product.selling_price >= min_price)
        if max_price is not None:
            filters.append(Product.selling_price <= max_price)
        if has_image is True:
            filters.extend(
                [Product.image_url.is_not(None), func.length(func.trim(Product.image_url)) > 0]
            )
        elif has_image is False:
            filters.append(
                or_(Product.image_url.is_(None), func.length(func.trim(Product.image_url)) == 0)
            )
        base = select(Product).where(*filters)
        discount = (Product.mrp - Product.selling_price) / func.nullif(Product.mrp, 0)
        ordering = {
            "low": Product.selling_price.asc(),
            "high": Product.selling_price.desc(),
            "newest": Product.created_at.desc(),
            "deals": discount.desc(),
        }.get(sort, Product.featured_score.desc())
        query = base.order_by(ordering, Product.id)
        if size:
            query = query.offset((page - 1) * size).limit(size)
        products = list(await self.session.scalars(query))
        total = await self.session.scalar(select(func.count(Product.id)).where(*filters)) or 0
        return [self.product_read(item) for item in products], total

    async def product_facets(self, kind: str, search: str | None = None) -> list[dict[str, Any]]:
        dimensions = {
            "categories": (Product.category_l1, Product.category_l2),
            "brands": (Product.brand,),
            "units": (Product.unit, Product.unit_value),
            "taxes": (Product.tax_percent, Product.currency),
            "variations": (Product.unit, Product.unit_value, Product.color_hex),
        }
        columns = dimensions[kind]
        query = (
            select(
                *columns,
                func.count(Product.id).label("product_count"),
                func.count(Product.id).filter(Product.is_active.is_(True)).label("active_count"),
            )
            .where(Product.archived.is_(False))
            .group_by(*columns)
        )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(*[func.cast(column, String).ilike(pattern) for column in columns])
            )
        rows = (await self.session.execute(query.order_by(*columns))).all()
        keys = {
            "categories": ("category_l1", "category_l2"),
            "brands": ("brand",),
            "units": ("unit", "unit_value"),
            "taxes": ("tax_percent", "currency"),
            "variations": ("unit", "unit_value", "color_hex"),
        }[kind]
        result = []
        for row in rows:
            values = dict(zip(keys, row[: len(keys)]))
            if values.get(keys[0]) is None:
                continue
            result.append(
                {
                    **{
                        key: str(value) if value is not None else None
                        for key, value in values.items()
                    },
                    "product_count": row[-2],
                    "active_count": row[-1],
                }
            )
        return result

    async def create_product(self, payload: ProductCreate) -> ProductRead:
        values = payload.model_dump()
        self.add_default_image_url(values)
        for field in ("name", "platform_product_id", "canonical_slug", "barcode"):
            if not values.get(field):
                continue
            existing = await self.session.scalar(
                select(Product).where(getattr(Product, field) == values[field])
            )
            if existing:
                raise AppError(f"Product {field} already exists", 409)
        await self.sync_product_catalog(values)
        product = Product(**values)
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return ProductRead.model_validate(product)

    async def sync_product_catalog(self, values: dict[str, Any]) -> None:
        """Create catalog options referenced by manual entry or spreadsheet import."""
        l1_name = values["category_l1"].strip()
        main = await self.session.scalar(
            select(Category).where(func.lower(Category.name) == l1_name.lower())
        )
        if not main:
            main = Category(
                name=l1_name, slug=slugify(l1_name), parent_id=None, brands=[], priority=0
            )
            self.session.add(main)
            await self.session.flush()
        elif main.parent_id:
            raise AppError(f"{l1_name} is configured as an L2 subcategory, not an L1 category", 422)

        l2_name = (values.get("category_l2") or "").strip()
        if l2_name:
            sub = await self.session.scalar(
                select(Category).where(func.lower(Category.name) == l2_name.lower())
            )
            if not sub:
                self.session.add(
                    Category(
                        name=l2_name,
                        slug=slugify(l2_name),
                        parent_id=main.id,
                        brands=[],
                        priority=0,
                    )
                )
                await self.session.flush()
            elif sub.parent_id != main.id:
                raise AppError(f"{l2_name} is not assigned to the {l1_name} main category", 422)

        brand_name = (values.get("brand") or "").strip()
        if brand_name:
            brand = await self.session.scalar(
                select(Brand).where(func.lower(Brand.name) == brand_name.lower())
            )
            if not brand:
                self.session.add(Brand(name=brand_name, active=True))

        unit_name = values["unit"].strip()
        unit = await self.session.scalar(
            select(Unit).where(func.lower(Unit.name) == unit_name.lower())
        )
        if not unit:
            self.session.add(Unit(name=unit_name, active=True))
        await self.session.flush()

    async def import_products(self, payloads: list[ProductCreate]) -> ProductImportResult:
        platform_ids = [item.platform_product_id for item in payloads]
        if len(platform_ids) != len(set(platform_ids)):
            raise AppError("The import file contains duplicate platform_product_id values", 422)
        created = updated = unchanged = 0
        try:
            for row_number, payload in enumerate(payloads, start=2):
                values = payload.model_dump()
                self.add_default_image_url(values)
                product = await self.session.scalar(
                    select(Product).where(
                        Product.platform_product_id == values["platform_product_id"]
                    )
                )
                for field in ("canonical_slug", "name", "barcode"):
                    value = values.get(field)
                    if not value:
                        continue
                    conflict_query = select(Product).where(getattr(Product, field) == value)
                    if product:
                        conflict_query = conflict_query.where(Product.id != product.id)
                    if await self.session.scalar(conflict_query):
                        raise AppError(
                            f"Row {row_number}: {field} already belongs to another product", 409
                        )
                try:
                    await self.sync_product_catalog(values)
                except AppError as error:
                    raise AppError(
                        f"Row {row_number}: {error.message}", error.status_code
                    ) from error
                if not product:
                    self.session.add(Product(**values))
                    created += 1
                else:
                    changed = False
                    for field, value in values.items():
                        if getattr(product, field) != value:
                            setattr(product, field, value)
                            changed = True
                    if changed:
                        updated += 1
                    else:
                        unchanged += 1
                await self.session.flush()
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return ProductImportResult(
            total=len(payloads), created=created, updated=updated, unchanged=unchanged
        )

    @staticmethod
    def add_default_image_url(values: dict[str, Any]) -> None:
        supplied = (values.get("image_url") or "").strip()
        if supplied:
            values["image_url"] = supplied.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
            return
        slug = values["canonical_slug"].strip().removesuffix(".webp")
        values["image_url"] = f"{slug}.webp"

    async def delete_product(self, product_id: UUID) -> None:
        product = await self.session.get(Product, product_id)
        if not product:
            raise AppError("Product not found", 404)
        used_in_order = await self.session.scalar(
            select(OrderItem.id).where(OrderItem.product_id == product_id).limit(1)
        )
        if used_in_order:
            product.archived = True
            product.is_active = False
            product.stock_status = "out_of_stock"
            await self.session.commit()
            return
        await self.session.delete(product)
        await self.session.commit()

    async def get_product(self, product_id: UUID) -> ProductRead:
        product = await self.session.get(Product, product_id)
        if not product:
            raise AppError("Product not found", 404)
        return self.product_read(product)

    async def update_product(self, product_id: UUID, payload: ProductCreate) -> ProductRead:
        product = await self.session.get(Product, product_id)
        if not product:
            raise AppError("Product not found", 404)
        values = payload.model_dump()
        self.add_default_image_url(values)
        for field in ("platform_product_id", "canonical_slug", "name", "barcode"):
            value = values.get(field)
            if not value:
                continue
            conflict = await self.session.scalar(
                select(Product).where(getattr(Product, field) == value, Product.id != product_id)
            )
            if conflict:
                raise AppError(f"Product {field} already exists", 409)
        await self.sync_product_catalog(values)
        for field, value in values.items():
            setattr(product, field, value)
        await self.session.commit()
        await self.session.refresh(product)
        return self.product_read(product)

    async def upload_product_image(self, product_id: UUID, upload: UploadFile) -> ProductRead:
        product = await self.session.get(Product, product_id)
        if not product:
            raise AppError("Product not found", 404)
        storage = R2Storage()
        content, extension = await storage.read_image(upload)
        filename = f"{product.canonical_slug}{extension}"
        for size in ("s", "m", "l"):
            await storage.put(
                f"{product.platform_product_id}/{size}/{filename}",
                content,
                upload.content_type or "image/webp",
            )
        product.image_url = filename
        await self.session.commit()
        await self.session.refresh(product)
        return self.product_read(product)

    async def upload_brand_image(self, brand_id: UUID, upload: UploadFile) -> Brand:
        brand = await self.session.get(Brand, brand_id)
        if not brand:
            raise AppError("Brand not found", 404)
        storage = R2Storage()
        content, extension = await storage.read_image(upload)
        filename = storage.safe_filename(brand.name, extension)
        key = f"brands/{brand.id}/{filename}"
        await storage.put(key, content, upload.content_type or "image/webp")
        brand.image_url = storage.public_url(key)
        await self.session.commit()
        await self.session.refresh(brand)
        return brand

    @staticmethod
    def product_read(product: Product) -> ProductRead:
        return ProductRead.model_validate(product)
