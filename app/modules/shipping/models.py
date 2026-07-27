from sqlalchemy import Boolean, Float, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class ShippingZoneConfiguration(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "shipping_zone_configurations"

    store_name: Mapped[str] = mapped_column(String(160), default="SJS Super Market")
    store_address: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float, default=5)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
