from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class DeliveryInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    mobile: str = Field(min_length=7, max_length=20)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8, max_length=128)
    address: str
    photo_url: str | None = None
    zone: str
    vehicle_type: str
    vehicle_number: str
    documents: dict = {}
    bank_details: dict = {}
    verification_status: str = "pending"


class DeliveryPatch(BaseModel):
    name: str | None = None
    mobile: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    photo_url: str | None = None
    zone: str | None = None
    vehicle_type: str | None = None
    vehicle_number: str | None = None
    documents: dict | None = None
    bank_details: dict | None = None
    verification_status: str | None = None
    delivery_status: str | None = None
    online: bool | None = None
    active: bool | None = None
    blocked: bool | None = None
    latitude: float | None = None
    longitude: float | None = None


class DeliveryRead(BaseModel):
    id: UUID
    name: str
    mobile: str
    email: str
    address: str
    photo_url: str | None
    zone: str
    vehicle_type: str
    vehicle_number: str
    documents: dict
    bank_details: dict
    verification_status: str
    delivery_status: str
    online: bool
    active: bool
    blocked: bool
    rating: float
    total_deliveries: int
    completed_orders: int
    cancelled_orders: int
    failed_orders: int
    average_delivery_minutes: float
    latitude: float | None
    longitude: float | None
    last_active_at: datetime | None
    created_at: datetime
    active_order_id: UUID | None = None
    model_config = ConfigDict(from_attributes=True)


class AssignInput(BaseModel):
    order_id: UUID
    delivery_man_id: UUID


class LeaveDecision(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    admin_note: str | None = None


class NotificationInput(BaseModel):
    delivery_man_id: UUID | None = None
    kind: str = Field(pattern="^(order|broadcast|emergency|individual)$")
    title: str
    message: str


class ResetPasswordInput(BaseModel):
    password: str = Field(min_length=8, max_length=128)
