import asyncio
import logging
import os
from pathlib import Path
from collections.abc import Iterable

logger = logging.getLogger(__name__)


def _send_sync(tokens: list[str], title: str, body: str, data: dict[str, str]) -> int:
    if not tokens:
        return 0
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            from app.config import settings

            credential_path = (
                os.getenv("FIREBASE_CREDENTIALS_PATH") or settings.firebase_credentials_path
            )
            if credential_path:
                path = Path(credential_path)
                if not path.is_absolute():
                    path = Path(__file__).resolve().parents[3] / path
                firebase_admin.initialize_app(credentials.Certificate(path))
            else:
                firebase_admin.initialize_app()
        sent = 0
        for token in tokens:
            try:
                messaging.send(
                    messaging.Message(
                        token=token,
                        notification=messaging.Notification(title=title, body=body),
                        data=data,
                        android=messaging.AndroidConfig(
                            priority="high",
                            notification=messaging.AndroidNotification(
                                channel_id="sjs_notifications"
                            ),
                        ),
                    )
                )
                sent += 1
            except Exception:
                logger.exception("Firebase rejected a push notification")
        return sent
    except Exception:
        logger.exception(
            "Firebase is not configured. Set FIREBASE_CREDENTIALS_PATH to a service-account JSON file."
        )
        return 0


async def send_push(
    tokens: Iterable[str],
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    return await asyncio.to_thread(
        _send_sync,
        list(dict.fromkeys(tokens)),
        title,
        body,
        data or {},
    )
