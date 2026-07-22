from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
)
from app.db.engine import engine
from app.db.redis import init_redis, close_redis, get_redis_client
from app.api.v1.router import api_router

# Configure structured logging at import time
configure_logging()
logger = get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────
    logger.info("startup", service="api", env=settings.APP_ENV)
    init_redis()
    yield
    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("shutdown", service="api")
    await engine.dispose()
    await close_redis()


app = FastAPI(
    title="Security Intelligence Platform API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.APP_ENV == "production" else "/docs",
    redoc_url=None if settings.APP_ENV == "production" else "/redoc",
    openapi_url="/api/v1/openapi.json",
)

# ── Middleware (outermost first) ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ── Health endpoints ─────────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
async def health_check():
    return {"status": "ok", "service": "api"}


@app.get("/ready", tags=["ops"])
async def ready_check():
    errors: list[str] = []

    # Check DB
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("readiness.db_failed", error=str(exc))
        errors.append("database")

    # Check Redis
    try:
        redis = get_redis_client()
        await redis.ping()
    except Exception as exc:
        logger.error("readiness.redis_failed", error=str(exc))
        errors.append("redis")

    if errors:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "failed": errors},
        )
    return {"status": "ready", "checks": ["database", "redis"]}
