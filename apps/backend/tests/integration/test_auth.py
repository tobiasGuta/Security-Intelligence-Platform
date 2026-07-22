import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.security import hash_password

from sqlalchemy import select


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    result = await db_session.execute(select(User).where(User.username == "testuser"))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_login_success(test_client: AsyncClient, test_user: User):
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "csrf_token" in data

    # Check cookies
    cookies = dict(test_client.cookies)
    assert "__Host-session" in cookies


@pytest.mark.asyncio
async def test_login_invalid_credentials(test_client: AsyncClient, test_user: User):
    response = await test_client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "wrongpassword"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rate_limiting(test_client: AsyncClient, settings):
    # Make multiple failed login attempts
    for _ in range(settings.RATE_LIMIT_LOGIN_ATTEMPTS):
        await test_client.post(
            "/api/v1/auth/login",
            json={"username": "rate_limit_user", "password": "wrongpassword"},
        )

    # The next attempt should be rate limited
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"username": "rate_limit_user", "password": "wrongpassword"},
    )
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_get_me_authenticated(test_client: AsyncClient, test_user: User):
    # Login first
    await test_client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )

    response = await test_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(test_client: AsyncClient):
    response = await test_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_csrf_validation_logout_missing_token(
    test_client: AsyncClient, test_user: User
):
    # Login
    await test_client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )

    # Logout (Mutation) without Origin/Referer and CSRF Token
    response = await test_client.post("/api/v1/auth/logout")
    assert (
        response.status_code == 403
    )  # Should fail due to missing Origin/Referer first

    # Try with Origin but no CSRF Token
    response = await test_client.post(
        "/api/v1/auth/logout", headers={"Origin": "http://localhost:3000"}
    )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_csrf_validation_logout_success(
    test_client: AsyncClient, test_user: User
):
    # Login
    login_resp = await test_client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )
    csrf_token = login_resp.json()["csrf_token"]

    # Logout with valid CSRF Token and Origin
    response = await test_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200

    # Next request should be unauthorized
    response = await test_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_csrf_untrusted_origin(test_client: AsyncClient, test_user: User):
    # Login
    login_resp = await test_client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )
    csrf_token = login_resp.json()["csrf_token"]

    # Attempt logout with an untrusted origin
    response = await test_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://evil-attacker.com", "X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 403
    assert "Untrusted Origin or Referer" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cookie_attributes_development(
    test_client: AsyncClient, test_user: User, settings
):
    # Temporarily set to development
    prev = settings.APP_ENV
    settings.APP_ENV = "development"

    await test_client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )

    cookies = test_client.cookies
    assert "session" in cookies
    assert "__Host-session" not in cookies

    settings.APP_ENV = prev


@pytest.mark.asyncio
async def test_cookie_attributes_production(
    test_client: AsyncClient, test_user: User, settings
):
    # Temporarily set to production
    prev = settings.APP_ENV
    settings.APP_ENV = "production"

    response = await test_client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )

    # httpx doesn't perfectly expose cookie attributes like Secure directly in client.cookies dict,
    # but we can check the Set-Cookie headers
    set_cookie_headers = [
        v for k, v in response.headers.multi_items() if k.lower() == "set-cookie"
    ]
    assert any("__Host-session" in header for header in set_cookie_headers)
    assert any("Secure" in header for header in set_cookie_headers)

    settings.APP_ENV = prev
