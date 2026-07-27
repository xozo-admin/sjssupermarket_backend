from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AddressInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    mobile: str = Field(min_length=6, max_length=20)
    street: str = Field(min_length=2, max_length=300)
    locality: str | None = Field(default=None, max_length=180)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=120)
    pincode: str = Field(min_length=3, max_length=20)
    landmark: str | None = Field(default=None, max_length=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_default: bool = True


class AddressRead(AddressInput):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
