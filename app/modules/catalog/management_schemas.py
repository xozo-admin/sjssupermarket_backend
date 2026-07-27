from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class NamedEntityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    active: bool = True


class NamedEntityRead(NamedEntityCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BrandCreate(NamedEntityCreate):
    image_url: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    meta_image_url: str | None = None


class BrandRead(BrandCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    platform_product_id: str = Field(min_length=1, max_length=100)
    canonical_slug: str = Field(min_length=1, max_length=220)
    name: str = Field(min_length=2, max_length=200)
    short_description: str | None = None
    description_long: str | None = None
    category_l1: str = Field(min_length=1, max_length=150)
    category_l2: str | None = None
    brand: str | None = None
    currency: str = Field(default="INR", min_length=3, max_length=3)
    tax_percent: Decimal = Field(default=0, ge=0, le=100)
    selling_price: Decimal = Field(ge=0)
    mrp: Decimal = Field(ge=0)
    rating: Decimal = Field(default=0, ge=0, le=5)
    inventory_qty: int = Field(default=0, ge=0)
    stock_status: str = "in_stock"
    is_active: bool = True
    unit: str = Field(min_length=1, max_length=50)
    unit_value: Decimal = Field(default=1, gt=0)
    barcode: str | None = None
    featured_score: Decimal = Field(default=0, ge=0)
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    supplier_user_id: str | None = None
    image_url: str | None = None


class ProductRead(ProductCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    size: int
    pages: int


class ProductImportRequest(BaseModel):
    products: list[ProductCreate] = Field(min_length=1, max_length=30000)


class ProductImportResult(BaseModel):
    total: int
    created: int
    updated: int
    unchanged: int
