from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1)
    address_id: UUID
    payment_method: str = Field(pattern="^(cod|razorpay)$")


class OrderStatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(placed|pending|processing|assigned|accepted|picked_up|on_the_way|delivered|cancelled|failed)$"
    )


class OrderSummary(BaseModel):
    id: UUID
    total: Decimal
    status: str
    payment_status: str
    model_config = ConfigDict(from_attributes=True)


class OrderItemRead(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal
    model_config = ConfigDict(from_attributes=True)


class OrderRead(OrderSummary):
    user_id: UUID
    delivery_man_id: UUID | None = None
    delivery_man_name: str | None = None
    delivery_latitude: float | None = None
    delivery_longitude: float | None = None
    delivery_otp: str | None = None
    cod_collected: bool = False
    delivered_at: datetime | None = None
    delivery_proof_url: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_mobile: str | None = None
    payment_method: str
    subtotal: Decimal
    delivery_fee: Decimal
    delivery_address: str
    created_at: datetime
    items: list[OrderItemRead]
