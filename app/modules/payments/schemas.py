from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.orders.schemas import OrderItemCreate, OrderSummary


class RazorpayCheckoutCreate(BaseModel):
    address_id: UUID
    items: list[OrderItemCreate] = Field(min_length=1)


class RazorpayCheckoutRead(BaseModel):
    checkout_id: UUID
    razorpay_key_id: str
    razorpay_order_id: str
    amount: int
    display_amount: Decimal
    currency: str


class RazorpayVerify(BaseModel):
    checkout_id: UUID
    razorpay_order_id: str = Field(min_length=1, max_length=100)
    razorpay_payment_id: str = Field(min_length=1, max_length=100)
    razorpay_signature: str = Field(min_length=8, max_length=256)


class RazorpayVerifyResult(BaseModel):
    order: OrderSummary
    payment_status: str
