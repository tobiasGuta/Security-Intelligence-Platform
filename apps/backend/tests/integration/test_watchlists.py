import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.alert import AlertRule, AlertAction


@pytest.mark.asyncio
async def test_watchlist_user_ownership(db_session: AsyncSession):
    import uuid

    # Create two users
    u1_id = uuid.uuid4()
    u2_id = uuid.uuid4()
    user1 = User(
        id=u1_id, username="user1", email="user1@example.com", hashed_password="hashed"
    )
    user2 = User(
        id=u2_id, username="user2", email="user2@example.com", hashed_password="hashed"
    )
    db_session.add(user1)
    db_session.add(user2)
    await db_session.flush()

    # Create watchlist for user1
    wl1 = Watchlist(user_id=u1_id, name="User 1 Watchlist")
    db_session.add(wl1)
    await db_session.commit()

    # Alert rule for user 2 on user 1's watchlist (should not be allowed in application logic,
    # but at DB level we just check it saves properly, though a real app would enforce user_id match)
    # Let's verify we can query it properly by user.
    rule1 = AlertRule(
        user_id=user1.id,
        watchlist_id=wl1.id,
        name="Test Rule",
        cvss_threshold=7.0,
        action=AlertAction.IN_APP_NOTIFICATION,
    )
    db_session.add(rule1)
    await db_session.commit()

    # Ensure uniqueness of watchlist name per user
    wl2 = Watchlist(user_id=user1.id, name="User 1 Watchlist")
    db_session.add(wl2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()

    # But user 2 can have the same watchlist name
    wl3 = Watchlist(user_id=u2_id, name="User 1 Watchlist")
    db_session.add(wl3)
    await db_session.commit()

    stmt = select(Watchlist).where(Watchlist.user_id == u2_id)
    results = (await db_session.execute(stmt)).scalars().all()
    assert len(results) == 1
    assert results[0].name == "User 1 Watchlist"
