from decimal import Decimal
from uuid import UUID
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class RefundConfiguration(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "refund_configurations"
    allowed_days: Mapped[int] = mapped_column(Integer, default=7)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class RefundRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "refund_requests"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), index=True)
    order_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="RESTRICT"), unique=True, index=True
    )
    reason: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
