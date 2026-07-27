from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PosLineInput(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=999)


class PosSaleInput(BaseModel):
    items: list[PosLineInput] = Field(min_length=1)
    customer_name: str | None = Field(default=None, max_length=150)
    customer_mobile: str | None = Field(default=None, max_length=30)
    discount_type: str = Field(default="fixed", pattern="^(fixed|percent)$")
    discount_value: Decimal = Field(default=0, ge=0)
    payment_method: str = Field(default="cash", pattern="^(cash|razorpay)$")
    amount_tendered: Decimal = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=1000)


class PosSaleItemRead(BaseModel):
    product_id: UUID
    product_name: str
    barcode: str | None
    quantity: int
    unit_price: Decimal
    tax_percent: Decimal
    line_total: Decimal
    model_config = ConfigDict(from_attributes=True)


class PosSaleRead(BaseModel):
    id: UUID
    invoice_number: str
    status: str
    customer_name: str | None
    customer_mobile: str | None
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    payment_method: str
    payment_status: str
    amount_tendered: Decimal
    change_due: Decimal
    item_count: int
    notes: str | None
    created_at: datetime
    items: list[PosSaleItemRead]
    model_config = ConfigDict(from_attributes=True)


class PosRazorpayCheckoutRead(BaseModel):
    pos_sale_id: UUID
    razorpay_key_id: str
    razorpay_order_id: str
    amount: int
    display_amount: Decimal
    currency: str


class PosRazorpayVerify(BaseModel):
    pos_sale_id: UUID
    razorpay_order_id: str = Field(min_length=1, max_length=100)
    razorpay_payment_id: str = Field(min_length=1, max_length=100)
    razorpay_signature: str = Field(min_length=8, max_length=256)
