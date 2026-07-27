from __future__ import annotations

from decimal import Decimal
from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class NamedCatalogEntity(UUIDMixin, TimestampMixin):
    __abstract__ = True
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Variation(NamedCatalogEntity, Base):
    __tablename__ = "variations"


class Unit(NamedCatalogEntity, Base):
    __tablename__ = "units"


class Tax(NamedCatalogEntity, Base):
    __tablename__ = "taxes"


class Brand(NamedCatalogEntity, Base):
    __tablename__ = "brands"
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta_title: Mapped[str | None] = mapped_column(String(170), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"
    platform_product_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    canonical_slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_long: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_l1: Mapped[str] = mapped_column(String(150), index=True)
    category_l2: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    mrp: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)
    inventory_qty: Mapped[int] = mapped_column(Integer, default=0)
    stock_status: Mapped[str] = mapped_column(String(30), default="in_stock", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    unit: Mapped[str] = mapped_column(String(50))
    unit_value: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=1)
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    featured_score: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, index=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    supplier_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
