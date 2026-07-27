from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    sku: str = Field(min_length=2, max_length=50)
    price: Decimal = Field(gt=0)
    unit: str = Field(default="piece", max_length=30)


class ProductRead(ProductCreate):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
