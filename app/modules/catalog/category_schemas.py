from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    parent_id: UUID | None = None
    brands: list[str] = Field(default_factory=list)
    priority: int = Field(default=0, ge=0, le=9999)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    meta_title: str | None = Field(default=None, max_length=170)
    meta_description: str | None = Field(default=None, max_length=1000)
    meta_image_url: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    parent_id: UUID | None = None
    brands: list[str] | None = None
    priority: int | None = Field(default=None, ge=0, le=9999)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    meta_title: str | None = Field(default=None, max_length=170)
    meta_description: str | None = Field(default=None, max_length=1000)
    meta_image_url: str | None = Field(default=None, max_length=500)


class CategoryRead(CategoryBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime
    parent_name: str | None = None
    product_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CategoryList(BaseModel):
    items: list[CategoryRead]
    total: int
    page: int
    size: int
