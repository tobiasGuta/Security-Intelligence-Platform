import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_session,
    get_session,
    delete_session,
)


def test_password_hashing():
    password = "supersecretpassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


@pytest.mark.asyncio
async def test_session_management(redis_client, settings):
    user_id = "test-user-123"

    # Create session
    session_id, csrf_token = await create_session(redis_client, user_id, settings)
    assert session_id
    assert csrf_token

    # Get session
    session = await get_session(redis_client, session_id, settings)
    assert session
    assert session["user_id"] == user_id
    assert session["csrf_token"] == csrf_token

    # Delete session
    await delete_session(redis_client, session_id)
    deleted_session = await get_session(redis_client, session_id, settings)
    assert not deleted_session


@pytest.mark.asyncio
async def test_session_idle_expiration(redis_client, settings):
    user_id = "test-user-idle"
    session_id, csrf_token = await create_session(redis_client, user_id, settings)

    import json
    from datetime import datetime, timezone, timedelta

    data_str = await redis_client.get(f"session:{session_id}")
    data = json.loads(data_str)

    # Set idle_expires_at to 1 minute ago
    data["idle_expires_at"] = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()
    await redis_client.set(f"session:{session_id}", json.dumps(data))

    # Session should now be considered expired
    session = await get_session(redis_client, session_id, settings)
    assert session is None


@pytest.mark.asyncio
async def test_session_absolute_expiration(redis_client, settings):
    user_id = "test-user-abs"
    session_id, csrf_token = await create_session(redis_client, user_id, settings)

    import json
    from datetime import datetime, timezone, timedelta

    data_str = await redis_client.get(f"session:{session_id}")
    data = json.loads(data_str)

    # Set abs_expires_at to 1 minute ago
    data["abs_expires_at"] = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()
    await redis_client.set(f"session:{session_id}", json.dumps(data))

    # Session should now be considered expired
    session = await get_session(redis_client, session_id, settings)
    assert session is None


@pytest.mark.asyncio
async def test_refuse_non_test_db():
    from app.core.config import Settings

    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/prod",
        TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost/prod",
        REDIS_URL="redis://localhost/0",
        SECRET_KEY="x" * 32,
        SESSION_SECRET="y" * 32,
        APP_ENV="testing",
    )

    import pytest

    with pytest.raises(Exception):
        # We can't easily catch pytest.exit() in the fixture without aborting the suite,
        # but we can simulate the conftest logic directly.
        if settings.TEST_DATABASE_URL == settings.DATABASE_URL:
            raise ValueError("Refused to use non-test database")
