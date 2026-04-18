from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import api_router_v1, integration_settings, users
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.scheduler_service import shutdown_scheduler, start_scheduler

# 需要从 422 验证错误中移除 input 的敏感字段名
_SENSITIVE_FIELDS = frozenset({"password", "new_password", "confirm_password"})


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

    # 自定义 422 处理：剥离敏感字段的 input 值，防止密码明文泄露
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for err in exc.errors():
            # 如果错误字段是敏感字段，移除 input 值
            field_name = err.get("loc", [])[-1] if err.get("loc") else None
            if field_name in _SENSITIVE_FIELDS:
                err = {k: v for k, v in err.items() if k != "input"}
            errors.append(err)
        return JSONResponse(status_code=422, content={"detail": errors})

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

