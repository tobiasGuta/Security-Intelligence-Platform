import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from redis.asyncio import Redis

from app.core.config import get_settings
from app.main import app as fastapi_app
from app.core.deps import get_db


@pytest.fixture(scope="session")
def settings():
    settings = get_settings()

    if settings.APP_ENV != "testing":
        pytest.exit("APP_ENV must be 'testing' to run tests.")
    if not settings.TEST_DATABASE_URL:
        pytest.exit("TEST_DATABASE_URL must be set.")
    if settings.TEST_DATABASE_URL == settings.DATABASE_URL:
        pytest.exit("TEST_DATABASE_URL must differ from DATABASE_URL.")
    if not settings.TEST_DATABASE_URL.endswith("_test"):
        pytest.exit("Test database name must end in '_test'.")

    # Use Redis DB 1 for testing
    from urllib.parse import urlparse

    parsed_redis = urlparse(settings.REDIS_URL)
    settings.REDIS_URL = f"{parsed_redis.scheme}://{parsed_redis.netloc}/1"

    return settings


@pytest.fixture(scope="session", autouse=True)
def setup_database(settings):
    # Ensure database exists if possible, but postgres-test container should create it
    # We will just run Alembic upgrade head
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.TEST_DATABASE_URL)

    # Run Alembic migrations synchronously
    command.upgrade(alembic_cfg, "head")

    yield

    # Do not downgrade, let the schema persist. Transactions handle isolation.


@pytest_asyncio.fixture
async def db_session(settings):
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(settings.TEST_DATABASE_URL, poolclass=NullPool)
    connection = await engine.connect()
    transaction = await connection.begin()

    async_session = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async with async_session() as session:
        yield session

    await transaction.rollback()
    await connection.close()
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
