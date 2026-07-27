from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class CustomerAddressSummary(BaseModel):
    id: UUID
    label: str
    is_default: bool


class CustomerOrderSummary(BaseModel):
    id: UUID
    total: Decimal
    status: str
    created_at: datetime


class CustomerAdminRead(BaseModel):
    id: UUID
    name: str
    email: str
    mobile: str | None
    active: bool
    created_at: datetime
    order_count: int
    total_spent: Decimal
    refund_count: int
    addresses: list[CustomerAddressSummary]
    recent_orders: list[CustomerOrderSummary]


class CustomerStatusInput(BaseModel):
    active: bool
