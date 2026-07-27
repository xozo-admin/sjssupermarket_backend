from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select

from app.modules.auth.dependencies import require_permission
from app.modules.auth.model import User
from app.modules.catalog.management_models import Product
from app.modules.customers.address_router import DbSession
from app.modules.pos.models import PosSale, PosSaleItem
from app.modules.pos.schemas import (
    PosRazorpayCheckoutRead,
    PosRazorpayVerify,
    PosSaleInput,
    PosSaleItemRead,
    PosSaleRead,
)
from app.modules.payments.razorpay import (
    create_provider_order,
    fetch_payment,
    verify_payment_signature,
)
from app.config import settings

router = APIRouter()
AdminUser = User
pos_user = require_permission("pos.manage")
money = Decimal("0.01")


async def _serialize(session, sales: list[PosSale]) -> list[PosSaleRead]:
    ids = [sale.id for sale in sales]
    items = (
        list(
            await session.scalars(
                select(PosSaleItem)
                .where(PosSaleItem.sale_id.in_(ids))
                .order_by(PosSaleItem.created_at)
            )
        )
        if ids
        else []
    )
    grouped = {sale_id: [] for sale_id in ids}
    for item in items:
        grouped[item.sale_id].append(PosSaleItemRead.model_validate(item))
    return [
        PosSaleRead.model_validate({**sale.__dict__, "items": grouped[sale.id]}) for sale in sales
    ]


@router.get("/products")
async def pos_products(
    session: DbSession,
    _: User = Depends(pos_user),
    search: str = "",
    limit: int = Query(default=500, ge=1, le=1000),
):
    query = select(Product).where(
        Product.archived.is_(False),
    )
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Product.name.ilike(term),
                Product.barcode.ilike(term),
                Product.platform_product_id.ilike(term),
            )
        )
    products = list(await session.scalars(query.order_by(Product.name).limit(limit)))
    return [
        {
            "id": product.id,
            "name": product.name,
            "barcode": product.barcode,
            "selling_price": product.selling_price,
            "mrp": product.mrp,
            "tax_percent": product.tax_percent,
            "inventory_qty": product.inventory_qty,
            "is_active": product.is_active,
            "stock_status": product.stock_status,
            "unit": product.unit,
            "image_url": product.image_url,
            "category": product.category_l1,
        }
        for product in products
    ]


async def _create_sale(payload: PosSaleInput, session: DbSession, user: User, held: bool):
    quantities: dict[UUID, int] = {}
    for item in payload.items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
    products = list(
        await session.scalars(select(Product).where(Product.id.in_(quantities)).with_for_update())
    )
    if len(products) != len(quantities):
        raise HTTPException(status_code=400, detail="One or more products are unavailable")
    for product in products:
        if (
            product.archived
            or not product.is_active
            or product.inventory_qty < quantities[product.id]
        ):
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}")
    subtotal = sum(
        (product.selling_price * quantities[product.id] for product in products),
        Decimal("0"),
    ).quantize(money)
    if payload.discount_type == "percent":
        if payload.discount_value > 100:
            raise HTTPException(status_code=400, detail="Discount cannot exceed 100%")
        discount = (subtotal * payload.discount_value / 100).quantize(money)
    else:
        discount = min(payload.discount_value, subtotal).quantize(money)
    total = (subtotal - discount).quantize(money)
    tax = sum(
        (
            (product.selling_price * quantities[product.id])
            * product.tax_percent
            / (Decimal("100") + product.tax_percent)
            for product in products
            if product.tax_percent
        ),
        Decimal("0"),
    ).quantize(money, rounding=ROUND_HALF_UP)
    tendered = payload.amount_tendered.quantize(money)
    if not held and payload.payment_method == "cash" and tendered < total:
        raise HTTPException(status_code=400, detail="Cash received is less than the bill total")
    now = datetime.now()
    invoice = f"POS-{now:%Y%m%d}-{now:%H%M%S%f}"[:-3]
    sale = PosSale(
        invoice_number=invoice,
        cashier_id=user.id,
        status="held" if held else "completed",
        customer_name=payload.customer_name.strip() if payload.customer_name else None,
        customer_mobile=payload.customer_mobile.strip() if payload.customer_mobile else None,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        payment_method=payload.payment_method,
        payment_status="pending" if held else "paid",
        amount_tendered=tendered,
        change_due=max(Decimal("0"), tendered - total) if not held else Decimal("0"),
        item_count=sum(quantities.values()),
        notes=payload.notes,
    )
    session.add(sale)
    await session.flush()
    for product in products:
        quantity = quantities[product.id]
        session.add(
            PosSaleItem(
                sale_id=sale.id,
                product_id=product.id,
                product_name=product.name,
                barcode=product.barcode,
                quantity=quantity,
                unit_price=product.selling_price,
                tax_percent=product.tax_percent,
                line_total=(product.selling_price * quantity).quantize(money),
            )
        )
        if not held:
            product.inventory_qty -= quantity
            if product.inventory_qty == 0:
                product.stock_status = "out_of_stock"
    await session.commit()
    await session.refresh(sale)
    return (await _serialize(session, [sale]))[0]


@router.post("/razorpay/create-order", response_model=PosRazorpayCheckoutRead)
async def create_pos_razorpay_order(
    payload: PosSaleInput,
    session: DbSession,
    user: User = Depends(pos_user),
):
    online_payload = payload.model_copy(
        update={"payment_method": "razorpay", "amount_tendered": Decimal("0")}
    )
    sale_read = await _create_sale(online_payload, session, user, held=True)
    sale = await session.get(PosSale, sale_read.id)
    if not sale:
        raise HTTPException(status_code=500, detail="Could not create POS payment")
    amount_minor = int((sale.total * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    provider_order = await create_provider_order(amount_minor, str(sale.id), str(user.id))
    provider_order_id = str(provider_order.get("id") or "")
    if not provider_order_id:
        raise HTTPException(status_code=502, detail="Razorpay returned an invalid order")
    sale.provider_order_id = provider_order_id
    await session.commit()
    return PosRazorpayCheckoutRead(
        pos_sale_id=sale.id,
        razorpay_key_id=settings.razorpay_key_id,
        razorpay_order_id=provider_order_id,
        amount=amount_minor,
        display_amount=sale.total,
        currency=settings.razorpay_currency.upper(),
    )


@router.post("/razorpay/verify", response_model=PosSaleRead)
async def verify_pos_razorpay_payment(
    payload: PosRazorpayVerify,
    session: DbSession,
    _: User = Depends(pos_user),
):
    sale = await session.scalar(
        select(PosSale).where(PosSale.id == payload.pos_sale_id).with_for_update()
    )
    if not sale:
        raise HTTPException(status_code=404, detail="POS payment session not found")
    if sale.status == "completed" and sale.payment_status == "paid":
        return (await _serialize(session, [sale]))[0]
    if sale.provider_order_id != payload.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Razorpay order mismatch")
    if not verify_payment_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    ):
        raise HTTPException(status_code=400, detail="Invalid Razorpay signature")
    payment = await fetch_payment(payload.razorpay_payment_id)
    expected_minor = int((sale.total * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if str(payment.get("order_id") or "") != sale.provider_order_id:
        raise HTTPException(status_code=400, detail="Razorpay order mismatch")
    if int(payment.get("amount") or 0) != expected_minor:
        raise HTTPException(status_code=400, detail="Razorpay amount mismatch")
    if str(payment.get("currency") or "").upper() != settings.razorpay_currency.upper():
        raise HTTPException(status_code=400, detail="Razorpay currency mismatch")
    if str(payment.get("status") or "").lower() != "captured":
        raise HTTPException(status_code=409, detail="Payment has not been captured")
    sale_items = list(
        await session.scalars(select(PosSaleItem).where(PosSaleItem.sale_id == sale.id))
    )
    quantities = {item.product_id: item.quantity for item in sale_items}
    products = list(
        await session.scalars(select(Product).where(Product.id.in_(quantities)).with_for_update())
    )
    if len(products) != len(quantities):
        raise HTTPException(status_code=409, detail="A billed product is no longer available")
    for product in products:
        if product.inventory_qty < quantities[product.id]:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}")
    for product in products:
        product.inventory_qty -= quantities[product.id]
        if product.inventory_qty == 0:
            product.stock_status = "out_of_stock"
    sale.status = "completed"
    sale.payment_status = "paid"
    sale.payment_method = "razorpay"
    sale.amount_tendered = sale.total
    sale.change_due = Decimal("0")
    sale.provider_payment_id = payload.razorpay_payment_id
    sale.provider_signature = payload.razorpay_signature
    await session.commit()
    await session.refresh(sale)
    return (await _serialize(session, [sale]))[0]


@router.post("/checkout", response_model=PosSaleRead, status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: PosSaleInput,
    session: DbSession,
    user: User = Depends(pos_user),
):
    return await _create_sale(payload, session, user, held=False)


@router.post("/hold", response_model=PosSaleRead, status_code=status.HTTP_201_CREATED)
async def hold_bill(
    payload: PosSaleInput,
    session: DbSession,
    user: User = Depends(pos_user),
):
    return await _create_sale(payload, session, user, held=True)


@router.get("/holds", response_model=list[PosSaleRead])
async def held_bills(session: DbSession, _: User = Depends(pos_user)):
    sales = list(
        await session.scalars(
            select(PosSale).where(PosSale.status == "held").order_by(PosSale.created_at.desc())
        )
    )
    return await _serialize(session, sales)


@router.delete("/holds/{sale_id}", status_code=204)
async def delete_hold(sale_id: UUID, session: DbSession, _: User = Depends(pos_user)):
    sale = await session.get(PosSale, sale_id)
    if not sale or sale.status != "held":
        raise HTTPException(status_code=404, detail="Held bill not found")
    await session.delete(sale)
    await session.commit()
    return Response(status_code=204)


@router.get("/sales", response_model=list[PosSaleRead])
async def recent_sales(
    session: DbSession,
    _: User = Depends(pos_user),
    limit: int = Query(default=20, ge=1, le=100),
):
    sales = list(
        await session.scalars(
            select(PosSale)
            .where(PosSale.status == "completed")
            .order_by(PosSale.created_at.desc())
            .limit(limit)
        )
    )
    return await _serialize(session, sales)
