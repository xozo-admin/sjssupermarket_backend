from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RefundConfigInput(BaseModel):
    allowed_days: int = Field(ge=1, le=365)
    enabled: bool


class RefundConfigRead(RefundConfigInput):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class RefundCreate(BaseModel):
    order_item_id: UUID
    reason: str = Field(min_length=5, max_length=1000)


class RefundDecision(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    admin_note: str | None = Field(default=None, max_length=1000)


class RefundRead(BaseModel):
    id: UUID
    user_id: UUID
    order_id: UUID
    order_item_id: UUID
    customer_name: str | None = None
    customer_mobile: str | None = None
    product_name: str
    amount: Decimal
    payment_method: str
    reason: str
    status: str
    admin_note: str | None
    created_at: datetime
