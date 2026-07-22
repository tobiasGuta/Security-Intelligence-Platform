import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from redis.asyncio import Redis

from app.core.config import get_settings
from app.db.base import Base
from app.main import app as fastapi_app
from app.core.deps import get_db
from app.db.redis import get_redis_client

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def settings():
    settings = get_settings()
    
    # Must use a dedicated test DB and Redis DB to prevent destruction of dev data
    from urllib.parse import urlparse
    
    parsed_db = urlparse(settings.DATABASE_URL)
    db_name = parsed_db.path.lstrip('/')
    if db_name in ("sip", "postgres", "production"):
        test_db_url = settings.DATABASE_URL + "_test"
    else:
        test_db_url = settings.DATABASE_URL
        
    settings.DATABASE_URL = test_db_url
    settings.APP_ENV = "testing"
    
    # Use Redis DB 1 for testing (isolated from dev DB 0)
    parsed_redis = urlparse(settings.REDIS_URL)
    settings.REDIS_URL = f"{parsed_redis.scheme}://{parsed_redis.netloc}/1"
    
    return settings

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database(settings):
    if settings.APP_ENV in ("development", "production"):
        pytest.exit("Tests must not run against development or production databases.")
        
    from sqlalchemy.ext.asyncio import create_async_engine
    from urllib.parse import urlparse
    
    base_url = settings.DATABASE_URL.removesuffix("_test")
    parsed = urlparse(base_url)
    default_url = f"{parsed.scheme}://{parsed.netloc}/postgres"
    
    provision_engine = create_async_engine(default_url, isolation_level="AUTOCOMMIT")
    async with provision_engine.connect() as conn:
        test_db_name = urlparse(settings.DATABASE_URL).path.lstrip('/')
        res = await conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{test_db_name}'"))
        if not res.scalar():
            await conn.execute(text(f"CREATE DATABASE {test_db_name}"))
            
    await provision_engine.dispose()
    
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(settings):
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()

@pytest_asyncio.fixture
async def redis_client(settings):
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    await redis.flushdb()
    yield redis
    await redis.close()

@pytest_asyncio.fixture
async def test_client(db_session, redis_client, settings):
    async def override_get_db():
        yield db_session
        
    async def override_get_redis():
        yield redis_client
        
    from app.core.deps import get_redis
    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_redis] = override_get_redis
    fastapi_app.dependency_overrides[get_settings] = lambda: settings
    
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
        
    fastapi_app.dependency_overrides.clear()
