from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from app.modules.auth.dependencies import require_permission
from app.modules.auth.model import User
from app.modules.catalog.management_models import Product
from app.modules.customers.address_router import DbSession
from app.modules.suppliers.models import Supplier, PurchaseOrder, PurchaseOrderItem

router = APIRouter()
Allowed = Annotated[User, Depends(require_permission("suppliers.manage"))]


class SupplierInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=160)
    contact_person: str | None = None
    email: EmailStr | None = None
    mobile: str = Field(min_length=7, max_length=30)
    gst_number: str | None = None
    address: str | None = None
    active: bool = True
    notes: str | None = None


class Line(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1)
    unit_cost: Decimal = Field(gt=0)
    tax_percent: Decimal = Field(default=0, ge=0, le=100)


class POInput(BaseModel):
    supplier_id: UUID
    expected_date: str | None = None
    items: list[Line] = Field(min_length=1)
    notes: str | None = None


class ReceiveLine(BaseModel):
    item_id: UUID
    quantity: int = Field(ge=1)


class ReceiveInput(BaseModel):
    items: list[ReceiveLine] = Field(min_length=1)


class PaymentInput(BaseModel):
    status: str = Field(pattern="^(unpaid|partial|paid)$")


def supplier_read(s):
    return {
        k: getattr(s, k)
        for k in [
            "id",
            "name",
            "contact_person",
            "email",
            "mobile",
            "gst_number",
            "address",
            "active",
            "notes",
            "created_at",
        ]
    }


async def po_read(db, orders):
    ids = [o.id for o in orders]
    items = (
        list(
            await db.scalars(
                select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id.in_(ids))
            )
        )
        if ids
        else []
    )
    suppliers = (
        list(
            await db.scalars(
                select(Supplier).where(Supplier.id.in_([o.supplier_id for o in orders]))
            )
        )
        if orders
        else []
    )
    sn = {s.id: s.name for s in suppliers}
    g = {i: [] for i in ids}
    for x in items:
        g[x.purchase_order_id].append(
            {
                k: getattr(x, k)
                for k in [
                    "id",
                    "product_id",
                    "product_name",
                    "quantity",
                    "received_quantity",
                    "unit_cost",
                    "tax_percent",
                    "line_total",
                ]
            }
        )
    return [
        {
            **{
                k: getattr(o, k)
                for k in [
                    "id",
                    "po_number",
                    "supplier_id",
                    "status",
                    "payment_status",
                    "expected_date",
                    "subtotal",
                    "tax",
                    "total",
                    "notes",
                    "created_at",
                ]
            },
            "supplier_name": sn.get(o.supplier_id, "Supplier"),
            "items": g[o.id],
        }
        for o in orders
    ]


@router.get("/suppliers")
async def suppliers(db: DbSession, _: Allowed):
    return [supplier_read(s) for s in await db.scalars(select(Supplier).order_by(Supplier.name))]


@router.post("/suppliers")
async def add_supplier(p: SupplierInput, db: DbSession, _: Allowed):
    s = Supplier(**p.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return supplier_read(s)


@router.put("/suppliers/{sid}")
async def edit_supplier(sid: UUID, p: SupplierInput, db: DbSession, _: Allowed):
    s = await db.get(Supplier, sid)
    if not s:
        raise HTTPException(404, "Supplier not found")
    for k, v in p.model_dump().items():
        setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    return supplier_read(s)


@router.get("/orders")
async def orders(db: DbSession, _: Allowed):
    return await po_read(
        db, list(await db.scalars(select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc())))
    )


@router.post("/orders")
async def create_order(p: POInput, db: DbSession, user: Allowed):
    if not await db.get(Supplier, p.supplier_id):
        raise HTTPException(404, "Supplier not found")
    products = {
        x.id: x
        for x in await db.scalars(
            select(Product).where(Product.id.in_([i.product_id for i in p.items]))
        )
    }
    if len(products) != len({i.product_id for i in p.items}):
        raise HTTPException(400, "Product not found")
    subtotal = sum((i.unit_cost * i.quantity for i in p.items), Decimal(0))
    tax = sum((i.unit_cost * i.quantity * i.tax_percent / 100 for i in p.items), Decimal(0))
    now = datetime.now()
    po = PurchaseOrder(
        po_number=f"PO-{now:%Y%m%d-%H%M%S%f}"[:-3],
        supplier_id=p.supplier_id,
        created_by=user.id,
        status="ordered",
        payment_status="unpaid",
        expected_date=p.expected_date,
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
        notes=p.notes,
    )
    db.add(po)
    await db.flush()
    for i in p.items:
        db.add(
            PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=i.product_id,
                product_name=products[i.product_id].name,
                quantity=i.quantity,
                unit_cost=i.unit_cost,
                tax_percent=i.tax_percent,
                line_total=i.unit_cost * i.quantity
                + i.unit_cost * i.quantity * i.tax_percent / 100,
            )
        )
    await db.commit()
    await db.refresh(po)
    return (await po_read(db, [po]))[0]


@router.post("/orders/{oid}/receive")
async def receive(oid: UUID, p: ReceiveInput, db: DbSession, _: Allowed):
    po = await db.get(PurchaseOrder, oid)
    if not po or po.status == "cancelled":
        raise HTTPException(404, "Purchase order not available")
    rows = {
        x.id: x
        for x in await db.scalars(
            select(PurchaseOrderItem)
            .where(PurchaseOrderItem.purchase_order_id == oid)
            .with_for_update()
        )
    }
    for r in p.items:
        item = rows.get(r.item_id)
        if not item or item.received_quantity + r.quantity > item.quantity:
            raise HTTPException(400, "Invalid received quantity")
        product = await db.get(Product, item.product_id, with_for_update=True)
        item.received_quantity += r.quantity
        product.inventory_qty += r.quantity
        if product.inventory_qty > 0:
            product.stock_status = "in_stock"
    po.status = (
        "received"
        if all(x.received_quantity == x.quantity for x in rows.values())
        else "partially_received"
    )
    await db.commit()
    await db.refresh(po)
    return (await po_read(db, [po]))[0]


@router.patch("/orders/{oid}/payment")
async def payment(oid: UUID, p: PaymentInput, db: DbSession, _: Allowed):
    po = await db.get(PurchaseOrder, oid)
    if not po:
        raise HTTPException(404, "Purchase order not found")
    po.payment_status = p.status
    await db.commit()
    await db.refresh(po)
    return (await po_read(db, [po]))[0]


@router.patch("/orders/{oid}/cancel")
async def cancel(oid: UUID, db: DbSession, _: Allowed):
    po = await db.get(PurchaseOrder, oid)
    if not po or po.status in {"received", "partially_received"}:
        raise HTTPException(400, "Received order cannot be cancelled")
    po.status = "cancelled"
    await db.commit()
    return {"message": "Cancelled"}
