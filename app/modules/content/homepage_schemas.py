from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.management_schemas import ProductRead


class HeroSlideCreate(BaseModel):
    subtitle: str | None = Field(default=None, max_length=180)
    title: str | None = Field(default=None, max_length=240)
    description: str | None = None
    badge_text: str | None = Field(default=None, max_length=120)
    button_text: str | None = Field(default=None, max_length=80)
    button_url: str | None = Field(default=None, max_length=500)
    delivery_text: str | None = Field(default=None, max_length=100)
    image_url: str | None = None
    active: bool = True
    sort_order: int = Field(default=0, ge=0, le=9999)


class HeroSlideRead(HeroSlideCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TopCategoriesUpdate(BaseModel):
    category_ids: list[UUID] = Field(default_factory=list, max_length=20)


class FreshPicksUpdate(BaseModel):
    product_ids: list[UUID] = Field(default_factory=list, max_length=20)


class HomepageBannerUpdate(BaseModel):
    eyebrow: str | None = Field(default=None, max_length=120)
    title: str | None = Field(default=None, max_length=240)
    description: str | None = None
    button_text: str | None = Field(default=None, max_length=80)
    button_url: str | None = Field(default=None, max_length=500)
    image_url: str | None = None
    active: bool = True


class HomepageBannerRead(HomepageBannerUpdate):
    id: UUID
    section_key: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClientFeedbackCreate(BaseModel):
    client_name: str = Field(min_length=1, max_length=120)
    client_role: str | None = Field(default=None, max_length=120)
    feedback: str = Field(min_length=1, max_length=2000)
    rating: int = Field(default=5, ge=1, le=5)
    avatar_url: str | None = None
    active: bool = True
    sort_order: int = Field(default=0, ge=0, le=9999)


class ClientFeedbackRead(ClientFeedbackCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StorefrontHomepageRead(BaseModel):
    hero_slides: list[HeroSlideRead] = Field(default_factory=list)
    top_category_ids: list[UUID] = Field(default_factory=list)
    fresh_pick_ids: list[UUID] = Field(default_factory=list)
    trending_product_ids: list[UUID] = Field(default_factory=list)
    banner_one: HomepageBannerRead | None = None
    weekly_deal_ids: list[UUID] = Field(default_factory=list)
    banner_two: HomepageBannerRead | None = None
    client_feedback: list[ClientFeedbackRead] = Field(default_factory=list)
    products: list[ProductRead] = Field(default_factory=list)
