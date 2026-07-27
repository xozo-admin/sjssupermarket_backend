from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class HeroSlide(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "hero_slides"

    subtitle: Mapped[str | None] = mapped_column(String(180), nullable=True)
    title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    badge_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    button_text: Mapped[str | None] = mapped_column(String(80), nullable=True)
    button_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delivery_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)


class HomepageTopCategory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "homepage_top_categories"

    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), unique=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)


class HomepageFreshPick(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "homepage_fresh_picks"

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), unique=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)


class HomepageTrendingProduct(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "homepage_trending_products"

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), unique=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)


class HomepageBanner(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "homepage_banners"

    section_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    eyebrow: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    button_text: Mapped[str | None] = mapped_column(String(80), nullable=True)
    button_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class HomepageWeeklyDeal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "homepage_weekly_deals"

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), unique=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)


class ClientFeedback(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "client_feedback"

    client_name: Mapped[str] = mapped_column(String(120))
    client_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    feedback: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer, default=5)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
