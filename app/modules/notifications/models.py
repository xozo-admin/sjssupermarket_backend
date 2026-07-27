from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class PushDevice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "push_devices"

    token: Mapped[str] = mapped_column(String(4096), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(20), default="android")
    app_kind: Mapped[str] = mapped_column(String(20), index=True)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    delivery_man_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("delivery_men.id", ondelete="CASCADE"), nullable=True, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
