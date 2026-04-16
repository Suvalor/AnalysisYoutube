from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import api_router_v1, integration_settings, users
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.scheduler_service import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Creator SaaS Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 速率限制
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router_v1, prefix="/api")
    # 部分网关会把 /api 前缀剥掉再转发到后端，补挂 /users/... 以免集成配置与域名校验 404
    app.include_router(users.router, prefix="/users")
    app.include_router(integration_settings.router, prefix="/users")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

