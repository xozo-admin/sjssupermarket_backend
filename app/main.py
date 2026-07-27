from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.config import settings
from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.middleware import register_middleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )
    register_middleware(app)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
