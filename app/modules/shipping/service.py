from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException
from sqlalchemy import select

from app.modules.shipping.models import ShippingZoneConfiguration


def distance_km(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    start_latitude = radians(latitude_a)
    end_latitude = radians(latitude_b)
    value = (
        sin(latitude_delta / 2) ** 2
        + cos(start_latitude) * cos(end_latitude) * sin(longitude_delta / 2) ** 2
    )
    return 6371 * 2 * asin(sqrt(value))


async def delivery_availability(
    session, latitude: float, longitude: float
) -> tuple[bool, float, ShippingZoneConfiguration | None]:
    zone = await session.scalar(select(ShippingZoneConfiguration).limit(1))
    if zone is None or not zone.enabled:
        return False, 0, zone
    distance = distance_km(zone.latitude, zone.longitude, latitude, longitude)
    return distance <= zone.radius_km, distance, zone


async def require_deliverable_address(session, address) -> ShippingZoneConfiguration:
    if address.latitude is None or address.longitude is None:
        raise HTTPException(status_code=400, detail="Select your delivery location on the map")
    available, distance, zone = await delivery_availability(
        session, address.latitude, address.longitude
    )
    if zone is None or not zone.enabled:
        raise HTTPException(status_code=400, detail="Delivery is currently unavailable")
    if not available:
        raise HTTPException(
            status_code=400,
            detail=f"Delivery is not available for your location. The address is {distance:.1f} km away; our delivery range is {zone.radius_km:g} km.",
        )
    return zone
