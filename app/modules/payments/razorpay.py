import asyncio
import base64
import hashlib
import hmac
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from app.config import settings


def ensure_configured() -> None:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured on the server")
    expected = settings.razorpay_environment.lower()
    actual = "live" if settings.razorpay_key_id.startswith("rzp_live_") else "test"
    if expected not in {"test", "live"} or actual != expected:
        raise HTTPException(status_code=503, detail="Razorpay key and environment do not match")


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    ensure_configured()
    token = base64.b64encode(
        f"{settings.razorpay_key_id}:{settings.razorpay_key_secret}".encode()
    ).decode()
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"{settings.razorpay_api_base.rstrip('/')}/{path.lstrip('/')}",
        data=body,
        method=method,
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode()).get("error", {}).get("description")
        except Exception:
            detail = None
        raise HTTPException(status_code=502, detail=detail or "Razorpay request failed") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail="Razorpay service is unreachable") from exc


async def create_provider_order(amount_minor: int, receipt: str, user_id: str) -> dict:
    return await asyncio.to_thread(
        _request,
        "POST",
        "/orders",
        {
            "amount": amount_minor,
            "currency": settings.razorpay_currency.upper(),
            "receipt": receipt[:40],
            "notes": {"checkout_id": receipt, "user_id": user_id},
        },
    )


async def fetch_payment(payment_id: str) -> dict:
    return await asyncio.to_thread(_request, "GET", f"/payments/{payment_id}")


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    message = f"{order_id}|{payment_id}".encode()
    digest = hmac.new(settings.razorpay_key_secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    if not settings.razorpay_webhook_secret:
        raise HTTPException(status_code=503, detail="Razorpay webhook is not configured")
    digest = hmac.new(settings.razorpay_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
