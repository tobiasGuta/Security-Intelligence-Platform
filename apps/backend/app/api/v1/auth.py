from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.core.config import get_settings, Settings
from app.core.security import verify_password, create_session, delete_session, check_rate_limit
from app.core.deps import get_db, get_redis, get_current_session, get_current_user, _get_cookie_name
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, CSRFResponse, UserResponse

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings)
):
    ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"rl:login:{ip}"
    
    if not await check_rate_limit(redis, rate_limit_key, settings.RATE_LIMIT_LOGIN_ATTEMPTS, settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")

    # If there is an existing session, delete it first
    cookie_name = _get_cookie_name(settings)
    old_session_id = request.cookies.get(cookie_name)
    if old_session_id:
        await delete_session(redis, old_session_id)

    session_id, csrf_token = await create_session(redis, str(user.id), settings)
    
    is_prod = settings.APP_ENV == "production"
    
    response.set_cookie(
        key=cookie_name,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        path="/",
        max_age=settings.SESSION_ABS_HOURS * 3600
    )
    
    return LoginResponse(csrf_token=csrf_token)

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: Dict = Depends(get_current_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings)
):
    cookie_name = _get_cookie_name(settings)
    session_id = request.cookies.get(cookie_name)
    if session_id:
        await delete_session(redis, session_id)
        
    response.delete_cookie(
        key=cookie_name,
        path="/",
        secure=settings.APP_ENV == "production",
        httponly=True,
        samesite="lax"
    )
    return {"status": "logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user

@router.get("/csrf", response_model=CSRFResponse)
async def get_csrf(session: Dict = Depends(get_current_session)):
    return CSRFResponse(csrf_token=session["csrf_token"])
