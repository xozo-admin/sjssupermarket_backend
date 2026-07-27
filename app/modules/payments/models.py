from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class PaymentCheckoutSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payment_checkout_sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    address_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_addresses.id", ondelete="RESTRICT"), index=True
    )
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(30), default="razorpay")
    provider_order_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    provider_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="created", index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount_minor: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    items: Mapped[list[dict]] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
