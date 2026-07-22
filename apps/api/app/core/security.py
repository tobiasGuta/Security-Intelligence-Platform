import secrets
import json
from datetime import datetime, timezone, timedelta
from typing import Tuple, Dict, Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.core.config import Settings
from redis.asyncio import Redis

ph = PasswordHasher(memory_cost=65536, time_cost=3, parallelism=4)

def hash_password(plain: str) -> str:
    return ph.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False

def generate_session_id() -> str:
    return secrets.token_hex(32)

def generate_csrf_token() -> str:
    return secrets.token_hex(32)

async def create_session(redis: Redis, user_id: str, settings: Settings) -> Tuple[str, str]:
    session_id = generate_session_id()
    csrf_token = generate_csrf_token()
    
    now = datetime.now(timezone.utc)
    idle_expires_at = now + timedelta(hours=settings.SESSION_IDLE_HOURS)
    abs_expires_at = now + timedelta(hours=settings.SESSION_ABS_HOURS)
    
    session_data = {
        "user_id": user_id,
        "csrf_token": csrf_token,
        "created_at": now.isoformat(),
        "last_seen_at": now.isoformat(),
        "idle_expires_at": idle_expires_at.isoformat(),
        "abs_expires_at": abs_expires_at.isoformat(),
    }
    
    # TTL should be max possible time
    ttl = int(settings.SESSION_ABS_HOURS * 3600)
    await redis.set(f"session:{session_id}", json.dumps(session_data), ex=ttl)
    
    return session_id, csrf_token

async def get_session(redis: Redis, session_id: str, settings: Settings) -> Optional[Dict]:
    data = await redis.get(f"session:{session_id}")
    if not data:
        return None
        
    session = json.loads(data)
    now = datetime.now(timezone.utc)
    
    idle_expires_at = datetime.fromisoformat(session["idle_expires_at"])
    abs_expires_at = datetime.fromisoformat(session["abs_expires_at"])
    
    if now > idle_expires_at or now > abs_expires_at:
        await delete_session(redis, session_id)
        return None
        
    # Update last_seen_at and idle_expires_at
    session["last_seen_at"] = now.isoformat()
    session["idle_expires_at"] = (now + timedelta(hours=settings.SESSION_IDLE_HOURS)).isoformat()
    
    ttl = int((abs_expires_at - now).total_seconds())
    if ttl > 0:
        await redis.set(f"session:{session_id}", json.dumps(session), ex=ttl)
        return session
    else:
        await delete_session(redis, session_id)
        return None

async def delete_session(redis: Redis, session_id: str) -> None:
    await redis.delete(f"session:{session_id}")

async def rotate_session_id(redis: Redis, old_session_id: str, settings: Settings) -> Tuple[str, str]:
    session = await get_session(redis, old_session_id, settings)
    await delete_session(redis, old_session_id)
    if not session:
        raise ValueError("Invalid session")
        
    return await create_session(redis, session["user_id"], settings)

async def check_rate_limit(redis: Redis, key: str, max_attempts: int, window_seconds: int) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    pipe = redis.pipeline()
    
    # Sliding window rate limit
    await pipe.zadd(key, {str(now): now})
    await pipe.zremrangebyscore(key, 0, now - window_seconds)
    await pipe.zcard(key)
    await pipe.expire(key, window_seconds)
    results = await pipe.execute()
    
    count = results[2]
    return count <= max_attempts
