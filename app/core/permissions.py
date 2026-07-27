from collections.abc import Callable

from fastapi import HTTPException, status

from app.core.enums import UserRole


def require_roles(*allowed: UserRole) -> Callable[[UserRole], UserRole]:
    def check(role: UserRole) -> UserRole:
        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return role

    return check
