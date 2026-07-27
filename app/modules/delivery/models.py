from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class DeliveryMan(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "delivery_men"
    name: Mapped[str] = mapped_column(String(120))
    mobile: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    zone: Mapped[str] = mapped_column(String(120), index=True)
    vehicle_type: Mapped[str] = mapped_column(String(80), index=True)
    vehicle_number: Mapped[str] = mapped_column(String(80))
    documents: Mapped[dict] = mapped_column(JSON, default=dict)
    bank_details: Mapped[dict] = mapped_column(JSON, default=dict)
    verification_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    delivery_status: Mapped[str] = mapped_column(String(30), default="available", index=True)
    online: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    rating: Mapped[float] = mapped_column(Float, default=0)
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0)
    failed_orders: Mapped[int] = mapped_column(Integer, default=0)
    average_delivery_minutes: Mapped[float] = mapped_column(Float, default=0)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeliveryAttendance(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "delivery_attendance"
    delivery_man_id: Mapped[UUID] = mapped_column(
        ForeignKey("delivery_men.id", ondelete="CASCADE"), index=True
    )
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    logout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    online_minutes: Mapped[int] = mapped_column(Integer, default=0)


class DeliveryEarning(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "delivery_earnings"
    delivery_man_id: Mapped[UUID] = mapped_column(
        ForeignKey("delivery_men.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cash_collected: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    online_payment: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    settlement_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)


class DeliveryLeave(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "delivery_leaves"
    delivery_man_id: Mapped[UUID] = mapped_column(
        ForeignKey("delivery_men.id", ondelete="CASCADE"), index=True
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class DeliveryNotification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "delivery_notifications"
    delivery_man_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("delivery_men.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)


class DeliveryActivity(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "delivery_activity_logs"
    delivery_man_id: Mapped[UUID] = mapped_column(
        ForeignKey("delivery_men.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
