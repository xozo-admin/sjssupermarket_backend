import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.database.session import SessionFactory
from app.modules.auth.model import User
from app.modules.delivery.models import DeliveryMan

router = APIRouter()


class DeliverySocketManager:
    def __init__(self):
        self.delivery: dict[UUID, set[WebSocket]] = defaultdict(set)
        self.admins: set[WebSocket] = set()
        self.customers: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect_delivery(self, man_id: UUID, socket: WebSocket):
        await socket.accept()
        async with self._lock:
            self.delivery[man_id].add(socket)

    async def connect_admin(self, socket: WebSocket):
        await socket.accept()
        async with self._lock:
            self.admins.add(socket)

    async def connect_customer(self, user_id: UUID, socket: WebSocket):
        await socket.accept()
        async with self._lock:
            self.customers[user_id].add(socket)

    async def disconnect(self, socket: WebSocket):
        async with self._lock:
            self.admins.discard(socket)
            for user_id, sockets in list(self.customers.items()):
                sockets.discard(socket)
                if not sockets:
                    self.customers.pop(user_id, None)
            for man_id, sockets in list(self.delivery.items()):
                sockets.discard(socket)
                if not sockets:
                    self.delivery.pop(man_id, None)

    async def _send(self, sockets: set[WebSocket], payload: dict):
        for socket in list(sockets):
            try:
                await socket.send_json(payload)
            except Exception:
                await self.disconnect(socket)

    async def to_delivery(self, man_id: UUID, event: str, data: dict | None = None):
        await self._send(
            set(self.delivery.get(man_id, set())), {"event": event, "data": data or {}}
        )

    async def to_all_delivery(self, event: str, data: dict | None = None):
        sockets = {socket for values in self.delivery.values() for socket in values}
        await self._send(sockets, {"event": event, "data": data or {}})

    async def to_admins(self, event: str, data: dict | None = None):
        await self._send(set(self.admins), {"event": event, "data": data or {}})

    async def to_customer(self, user_id: UUID, event: str, data: dict | None = None):
        await self._send(
            set(self.customers.get(user_id, set())), {"event": event, "data": data or {}}
        )


delivery_sockets = DeliverySocketManager()


@router.websocket("/delivery")
async def delivery_socket(socket: WebSocket, token: str = ""):
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        await socket.close(code=4401)
        return
    try:
        account_id = UUID(payload["sub"])
    except (TypeError, ValueError):
        await socket.close(code=4401)
        return
    role = payload.get("role")
    async with SessionFactory() as session:
        if role == "delivery":
            man = await session.get(DeliveryMan, account_id)
            if not man or not man.active or man.blocked:
                await socket.close(code=4403)
                return
            await delivery_sockets.connect_delivery(man.id, socket)
        elif role in {"admin", "staff"}:
            user = await session.get(User, account_id)
            if not user or not user.active or user.role not in {"admin", "staff"}:
                await socket.close(code=4403)
                return
            await delivery_sockets.connect_admin(socket)
        else:
            user = await session.get(User, account_id)
            if not user or not user.active:
                await socket.close(code=4403)
                return
            await delivery_sockets.connect_customer(user.id, socket)
    try:
        await socket.send_json({"event": "connected", "data": {"role": role}})
        while True:
            message = await socket.receive_text()
            if message == "ping":
                await socket.send_text("pong")
    except WebSocketDisconnect:
        await delivery_sockets.disconnect(socket)
    except Exception:
        await delivery_sockets.disconnect(socket)
