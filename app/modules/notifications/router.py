from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.database.session import get_db
from app.modules.auth.dependencies import current_user
from app.modules.auth.model import User
from app.modules.notifications.models import PushDevice
from app.modules.notifications.schemas import DeviceRegistration

router = APIRouter()
DbSession = Annotated[object, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/devices", status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceRegistration,
    session: DbSession,
    user: CurrentUser,
):
    device = await session.scalar(select(PushDevice).where(PushDevice.token == payload.token))
    if device is None:
        device = PushDevice(token=payload.token, platform=payload.platform, app_kind="customer")
        session.add(device)
    device.platform = payload.platform
    device.app_kind = "customer"
    device.user_id = user.id
    device.delivery_man_id = None
    device.active = True
    await session.commit()
    return {"ok": True}
