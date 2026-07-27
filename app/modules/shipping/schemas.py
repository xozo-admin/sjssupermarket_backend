from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ShippingZoneInput(BaseModel):
    store_name: str = Field(min_length=2, max_length=160)
    store_address: str = Field(default="", max_length=1000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(gt=0, le=500)
    delivery_fee: float = Field(ge=0, le=100000)
    enabled: bool = True


class ShippingZoneRead(ShippingZoneInput):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class DeliveryAvailability(BaseModel):
    available: bool
    distance_km: float
    radius_km: float | None
    message: str
