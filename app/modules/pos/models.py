from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class PosSale(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pos_sales"

    invoice_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    cashier_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="completed", index=True)
    customer_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    customer_mobile: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str] = mapped_column(String(20), default="cash")
    payment_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    provider_order_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    provider_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    amount_tendered: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    change_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PosSaleItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pos_sale_items"

    sale_id: Mapped[UUID] = mapped_column(
        ForeignKey("pos_sales.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(200))
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
