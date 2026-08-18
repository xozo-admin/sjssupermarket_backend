from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from app.config import settings
from app.modules.auth.model import User
from app.modules.catalog.management_models import Product
from app.modules.customers.address_model import CustomerAddress
from app.modules.customers.address_router import CurrentUser, DbSession
from app.modules.orders.models import Order
from app.modules.orders.router import create_customer_order
from app.modules.orders.schemas import OrderCreate, OrderItemCreate, OrderSummary
from app.modules.payments.models import PaymentCheckoutSession
from app.modules.payments.razorpay import (
    create_provider_order,
    fetch_payment,
    fetch_order_payments,
    verify_payment_signature,
    verify_webhook_signature,
)
from app.modules.payments.schemas import (
    RazorpayCheckoutCreate,
    RazorpayCheckoutRead,
    RazorpayVerify,
    RazorpayVerifyResult,
)
from app.modules.shipping.service import require_deliverable_address

router = APIRouter()


async def _price_checkout(payload: RazorpayCheckoutCreate, session: DbSession, user: User):
    address = await session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.id == payload.address_id,
            CustomerAddress.user_id == user.id,
        )
    )
    if not address:
        raise HTTPException(status_code=404, detail="Delivery address not found")
    await require_deliverable_address(session, address)
    quantities: dict[UUID, int] = {}
    for item in payload.items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
    products = list(await session.scalars(select(Product).where(Product.id.in_(quantities))))
    if len(products) != len(quantities):
        raise HTTPException(status_code=400, detail="One or more products are unavailable")
    for product in products:
        if (
            product.archived
            or not product.is_active
            or product.stock_status != "in_stock"
            or product.inventory_qty < quantities[product.id]
        ):
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}")
    subtotal = sum(
        (product.selling_price * quantities[product.id] for product in products),
        Decimal("0"),
    )
    # delivery_fee = Decimal("40") if subtotal < Decimal("500") else Decimal("0")
    delivery_fee = Decimal("0")
    return subtotal + delivery_fee


@router.post("/razorpay/create-order", response_model=RazorpayCheckoutRead)
async def create_razorpay_checkout(
    payload: RazorpayCheckoutCreate, session: DbSession, user: CurrentUser
):
    total = await _price_checkout(payload, session, user)
    amount_minor = int((total * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    checkout_id = uuid4()
    provider_order = await create_provider_order(amount_minor, str(checkout_id), str(user.id))
    provider_order_id = str(provider_order.get("id") or "")
    if not provider_order_id:
        raise HTTPException(status_code=502, detail="Razorpay returned an invalid order")
    checkout = PaymentCheckoutSession(
        id=checkout_id,
        user_id=user.id,
        address_id=payload.address_id,
        provider_order_id=provider_order_id,
        status="created",
        amount=total,
        amount_minor=amount_minor,
        currency=settings.razorpay_currency.upper(),
        items=[item.model_dump(mode="json") for item in payload.items],
    )
    session.add(checkout)
    await session.commit()
    return RazorpayCheckoutRead(
        checkout_id=checkout.id,
        razorpay_key_id=settings.razorpay_key_id,
        razorpay_order_id=checkout.provider_order_id,
        amount=checkout.amount_minor,
        display_amount=checkout.amount,
        currency=checkout.currency,
    )


async def _finalize(
    checkout: PaymentCheckoutSession,
    payment_id: str,
    signature: str,
    payment: dict,
    session: DbSession,
    user: User,
) -> Order:
    if checkout.order_id:
        order = await session.get(Order, checkout.order_id)
        if order:
            return order
    if str(payment.get("order_id")) != checkout.provider_order_id:
        raise HTTPException(status_code=400, detail="Razorpay order mismatch")
    if int(payment.get("amount") or 0) != checkout.amount_minor:
        raise HTTPException(status_code=400, detail="Razorpay amount mismatch")
    if str(payment.get("currency") or "").upper() != checkout.currency:
        raise HTTPException(status_code=400, detail="Razorpay currency mismatch")
    if str(payment.get("status") or "").lower() != "captured":
        raise HTTPException(status_code=409, detail="Payment has not been captured")
    payload = OrderCreate(
        address_id=checkout.address_id,
        payment_method="razorpay",
        items=[OrderItemCreate.model_validate(item) for item in checkout.items],
    )
    order = await create_customer_order(payload, session, user, payment_status="paid")
    checkout.order_id = order.id
    checkout.provider_payment_id = payment_id
    checkout.provider_signature = signature
    checkout.status = "paid"
    await session.commit()
    return order


@router.post("/razorpay/verify", response_model=RazorpayVerifyResult)
async def verify_razorpay_checkout(payload: RazorpayVerify, session: DbSession, user: CurrentUser):
    checkout = await session.scalar(
        select(PaymentCheckoutSession).where(
            PaymentCheckoutSession.id == payload.checkout_id,
            PaymentCheckoutSession.user_id == user.id,
        )
    )
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout session not found")
    if checkout.provider_order_id != payload.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Razorpay order mismatch")
    if not verify_payment_signature(
        checkout.provider_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    ):
        raise HTTPException(status_code=400, detail="Invalid Razorpay signature")
    payment = await fetch_payment(payload.razorpay_payment_id)
    order = await _finalize(
        checkout,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
        payment,
        session,
        user,
    )
    return RazorpayVerifyResult(order=OrderSummary.model_validate(order), payment_status="paid")

@router.get("/razorpay/check/{checkout_id}")
async def check_razorpay_payment(
    checkout_id: UUID,
    session: DbSession,
    user: CurrentUser,
):
    checkout = await session.scalar(
        select(PaymentCheckoutSession).where(
            PaymentCheckoutSession.id == checkout_id,
            PaymentCheckoutSession.user_id == user.id,
        )
    )

    if not checkout:
        raise HTTPException(
            status_code=404,
            detail="Checkout session not found",
        )

    # Already completed
    if checkout.order_id:
        order = await session.get(Order, checkout.order_id)

        if order:
            return {
                "payment_status": "paid",
                "order": OrderSummary.model_validate(order),
            }

    # Ask Razorpay for payments belonging to this Razorpay order
    result = await fetch_order_payments(
        checkout.provider_order_id
    )

    payments = result.get("items", [])

    captured_payment = next(
        (
            payment
            for payment in payments
            if str(payment.get("status", "")).lower() == "captured"
            and int(payment.get("amount") or 0) == checkout.amount_minor
            and str(payment.get("currency") or "").upper()
            == checkout.currency
        ),
        None,
    )

    if not captured_payment:
       return {
        "payment_status": "pending",
           "order": None,
        "razorpay_payments": [
            {
                "id": payment.get("id"),
                "status": payment.get("status"),
                "amount": payment.get("amount"),
                "currency": payment.get("currency"),
                "method": payment.get("method"),
                "order_id": payment.get("order_id"),
            }
            for payment in payments
        ],
    }

    payment_id = str(captured_payment.get("id") or "")

    order = await _finalize(
        checkout,
        payment_id,
        "",
        captured_payment,
        session,
        user,
    )

    return {
        "payment_status": "paid",
        "order": OrderSummary.model_validate(order),
    }

@router.post("/razorpay/webhook", status_code=204)
async def razorpay_webhook(
    request: Request,
    session: DbSession,
    x_razorpay_signature: str | None = Header(default=None),
):
    body = await request.body()
    if not x_razorpay_signature or not verify_webhook_signature(body, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay webhook signature")
    event = await request.json()
    if event.get("event") != "payment.captured":
        return
    payment = event.get("payload", {}).get("payment", {}).get("entity", {})
    provider_order_id = str(payment.get("order_id") or "")
    checkout = await session.scalar(
        select(PaymentCheckoutSession).where(
            PaymentCheckoutSession.provider_order_id == provider_order_id
        )
    )
    if not checkout or checkout.order_id:
        return
    user = await session.get(User, checkout.user_id)
    if not user:
        return
    await _finalize(checkout, str(payment.get("id") or ""), "", payment, session, user)
