import pytest
from app.core.security import hash_password, verify_password, create_session, get_session, delete_session

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
