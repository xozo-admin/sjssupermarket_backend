import argparse
import asyncio
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import SessionFactory
from app.modules.auth.model import User


async def create_admin(name: str, email: str, mobile: str | None) -> None:
    password = getpass("Admin password (minimum 8 characters): ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters")
    async with SessionFactory() as session:
        existing = await session.scalar(select(User).where(User.email == email.lower()))
        if existing:
            existing.name = name
            existing.mobile = mobile or existing.mobile
            existing.password_hash = hash_password(password)
            existing.role = "admin"
            existing.active = True
        else:
            session.add(
                User(
                    name=name,
                    email=email.lower(),
                    mobile=mobile,
                    password_hash=hash_password(password),
                    role="admin",
                    active=True,
                )
            )
        await session.commit()
    print(f"Admin account ready: {email.lower()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--mobile")
    args = parser.parse_args()
    asyncio.run(create_admin(args.name, args.email, args.mobile))
