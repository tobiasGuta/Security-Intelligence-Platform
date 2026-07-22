"""
FastAPI dependency functions.
"""
from typing import AsyncGenerator, Dict
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.db.session import get_async_session
from app.db.redis import get_redis_client
from app.core.config import get_settings, Settings
from app.core.security import get_session
from app.models.user import User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session() as session:
        yield session


async def get_redis() -> AsyncGenerator[Redis, None]:
    yield get_redis_client()


def _get_cookie_name(settings: Settings) -> str:
    """Return the correct cookie name based on environment."""
    return "session" if settings.APP_ENV == "development" else "__Host-session"


async def get_current_session(
    request: Request,
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> Dict:
    cookie_name = _get_cookie_name(settings)
    session_id = request.cookies.get(cookie_name)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    session = await get_session(redis, session_id, settings)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )

    return session


async def get_current_user(
    session: Dict = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session data",
        )

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


from redis.asyncio import Redis

async def verify_csrf(
    request: Request,
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate X-CSRF-Token header against the session token for state-changing requests."""
    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return
        
    if request.url.path == "/api/v1/auth/login":
        return

    # Check origin/referer
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    
    if not origin and not referer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing Origin or Referer header",
        )
        
    cookie_name = _get_cookie_name(settings)
    session_id = request.cookies.get(cookie_name)
    
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    session = await get_session(redis, session_id, settings)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    csrf_token = request.headers.get("X-CSRF-Token")
    session_csrf = session.get("csrf_token")
    
    import secrets
    if not csrf_token or not session_csrf or not secrets.compare_digest(csrf_token, session_csrf):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )
