from decimal import Decimal
from uuid import UUID
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.database.mixins import UUIDMixin, TimestampMixin


class Supplier(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"
    name: Mapped[str] = mapped_column(String(160), index=True)
    contact_person: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mobile: Mapped[str] = mapped_column(String(30), index=True)
    gst_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PurchaseOrder(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "purchase_orders"
    po_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(30), default="ordered", index=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="unpaid", index=True)
    expected_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PurchaseOrderItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "purchase_order_items"
    purchase_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
