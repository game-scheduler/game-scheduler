# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Integration tests for games database query patterns before guild_queries migration.

These tests establish behavioral baseline for GameService database operations.
Focus: Verify current database query behavior with minimal mocking.

IMPORTANT: Many tests document CURRENT INSECURE BEHAVIOR (no guild filtering in get_game).
After migration to guild_queries wrappers, tests must be updated to verify enforcement.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.cache.client import RedisClient
from shared.models.channel import ChannelConfiguration
from shared.models.game import GameSession, GameStatus
from shared.models.guild import GuildConfiguration
from shared.models.template import GameTemplate
from shared.models.user import User

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def db_url():
    """Get database URL from environment."""
    raw_url = os.getenv(
        "DATABASE_URL",
        "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
    )
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture
async def async_engine(db_url):
    """Create async engine for integration tests."""
    engine = create_async_engine(db_url, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
def async_session_factory(async_engine):
    """Create session factory for integration tests."""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest.fixture
async def db(async_session_factory):
    """Provide async database session for each test with automatic cleanup."""
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def redis_client():
    """Provide Redis client for cache operations."""
    client = RedisClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
def guild_a_id():
    """Guild A UUID for multi-guild testing - unique per test."""
    return str(uuid.uuid4())


@pytest.fixture
def guild_b_id():
    """Guild B UUID for multi-guild testing - unique per test."""
    return str(uuid.uuid4())


@pytest.fixture
async def guild_a_config(db, guild_a_id):
    """Create GuildConfiguration for guild_a."""
    guild_config = GuildConfiguration(
        id=guild_a_id,
        guild_id=str(uuid.uuid4())[:18],
    )
    db.add(guild_config)
    await db.flush()
    return guild_config


@pytest.fixture
async def guild_b_config(db, guild_b_id):
    """Create GuildConfiguration for guild_b for multi-guild testing."""
    guild_config = GuildConfiguration(
        id=guild_b_id,
        guild_id=str(uuid.uuid4())[:18],
    )
    db.add(guild_config)
    await db.flush()
    return guild_config


@pytest.fixture
async def channel_a(db, guild_a_id, guild_a_config):
    """Test channel for guild A."""
    channel = ChannelConfiguration(
        id=str(uuid.uuid4()),
        guild_id=guild_a_id,
        channel_id=str(uuid.uuid4())[:18],
        is_active=True,
    )
    db.add(channel)
    await db.flush()
    return channel


@pytest.fixture
async def channel_b(db, guild_b_id, guild_b_config):
    """Test channel for guild B."""
    channel = ChannelConfiguration(
        id=str(uuid.uuid4()),
        guild_id=guild_b_id,
        channel_id=str(uuid.uuid4())[:18],
        is_active=True,
    )
    db.add(channel)
    await db.flush()
    return channel


@pytest.fixture
async def template_a(db, guild_a_id, channel_a):
    """Test template for guild A."""
    template = GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=guild_a_id,
        channel_id=channel_a.id,
        name="Template A",
        description="Test template for guild A",
        order=0,
        is_default=True,
        max_players=4,
    )
    db.add(template)
    await db.flush()
    return template


@pytest.fixture
async def template_b(db, guild_b_id, channel_b):
    """Test template for guild B."""
    template = GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=guild_b_id,
        channel_id=channel_b.id,
        name="Template B",
        description="Test template for guild B",
        order=0,
        is_default=True,
        max_players=4,
    )
    db.add(template)
    await db.flush()
    return template


@pytest.fixture
async def user_a(db):
    """Test user for guild A."""
    user = User(
        id=str(uuid.uuid4()),
        discord_id=str(uuid.uuid4())[:18],
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def user_b(db):
    """Test user for guild B."""
    user = User(
        id=str(uuid.uuid4()),
        discord_id=str(uuid.uuid4())[:18],
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def game_a(db, guild_a_id, channel_a, template_a, user_a):
    """Test game in guild A."""
    game = GameSession(
        id=str(uuid.uuid4()),
        guild_id=guild_a_id,
        channel_id=channel_a.id,
        template_id=template_a.id,
        host_id=user_a.id,
        title="Game A",
        description="Test game in guild A",
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        max_players=4,
        status=GameStatus.SCHEDULED,
    )
    db.add(game)
    await db.flush()
    return game


@pytest.fixture
async def game_b(db, guild_b_id, channel_b, template_b, user_b):
    """Test game in guild B."""
    game = GameSession(
        id=str(uuid.uuid4()),
        guild_id=guild_b_id,
        channel_id=channel_b.id,
        template_id=template_b.id,
        host_id=user_b.id,
        title="Game B",
        description="Test game in guild B",
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        max_players=4,
        status=GameStatus.SCHEDULED,
    )
    db.add(game)
    await db.flush()
    return game


# Database Query Behavior Tests


@pytest.mark.asyncio
async def test_get_game_returns_any_game_without_guild_filter(db, game_a, game_b):
    """Verify current GameService.get_game: returns any game by ID, NO guild filtering.

    SECURITY GAP: This documents current insecure behavior.
    After migration: get_game should require guild_id parameter and enforce filtering.
    """
    from services.api.services.games import GameService
    from shared.messaging.publisher import EventPublisher

    service = GameService(
        db=db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    await db.commit()

    # Current: get_game returns ANY game by ID
    result_a = await service.get_game(game_a.id)
    assert result_a is not None
    assert result_a.id == game_a.id

    # SECURITY GAP: Also returns game from different guild
    result_b = await service.get_game(game_b.id)
    assert result_b is not None
    assert result_b.id == game_b.id


@pytest.mark.asyncio
async def test_list_games_filters_by_guild_when_specified(
    db, game_a, game_b, guild_a_id, guild_b_id
):
    """Verify list_games correctly filters by guild_id when parameter provided."""
    from services.api.services.games import GameService
    from shared.messaging.publisher import EventPublisher

    service = GameService(
        db=db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    await db.commit()

    # List games for guild A
    games_a, total_a = await service.list_games(guild_id=guild_a_id)
    assert total_a == 1
    assert len(games_a) == 1
    assert games_a[0].id == game_a.id
    assert games_a[0].guild_id == guild_a_id

    # List games for guild B
    games_b, total_b = await service.list_games(guild_id=guild_b_id)
    assert total_b == 1
    assert len(games_b) == 1
    assert games_b[0].id == game_b.id
    assert games_b[0].guild_id == guild_b_id


@pytest.mark.asyncio
async def test_list_games_with_channel_filter(db, game_a, channel_a, guild_a_id):
    """Verify list_games respects channel filter within guild."""
    from services.api.services.games import GameService
    from shared.messaging.publisher import EventPublisher

    service = GameService(
        db=db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    await db.commit()

    games, total = await service.list_games(guild_id=guild_a_id, channel_id=channel_a.id)
    assert total == 1
    assert len(games) == 1
    assert games[0].id == game_a.id
    assert games[0].channel_id == channel_a.id


@pytest.mark.asyncio
async def test_list_games_with_status_filter(db, game_a, guild_a_id):
    """Verify list_games respects status filter."""
    from services.api.services.games import GameService
    from shared.messaging.publisher import EventPublisher

    service = GameService(
        db=db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    await db.commit()

    # List scheduled games
    games, total = await service.list_games(guild_id=guild_a_id, status="SCHEDULED")
    assert total == 1
    assert games[0].status == GameStatus.SCHEDULED

    # List completed games (should be empty)
    games_completed, total_completed = await service.list_games(
        guild_id=guild_a_id, status="COMPLETED"
    )
    assert total_completed == 0
    assert len(games_completed) == 0


@pytest.mark.asyncio
async def test_list_games_pagination(db, guild_a_id, channel_a, template_a, user_a):
    """Verify list_games pagination works correctly."""
    from services.api.services.games import GameService
    from shared.messaging.publisher import EventPublisher

    # Create multiple games
    for i in range(5):
        game = GameSession(
            id=str(uuid.uuid4()),
            guild_id=guild_a_id,
            channel_id=channel_a.id,
            template_id=template_a.id,
            host_id=user_a.id,
            title=f"Game {i}",
            scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=i + 1),
            max_players=4,
            status=GameStatus.SCHEDULED,
        )
        db.add(game)

    await db.commit()

    service = GameService(
        db=db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    # Get first page
    games_page1, total = await service.list_games(guild_id=guild_a_id, limit=2, offset=0)
    assert total == 5
    assert len(games_page1) == 2

    # Get second page
    games_page2, total = await service.list_games(guild_id=guild_a_id, limit=2, offset=2)
    assert total == 5
    assert len(games_page2) == 2

    # Verify different games on each page
    page1_ids = {g.id for g in games_page1}
    page2_ids = {g.id for g in games_page2}
    assert len(page1_ids & page2_ids) == 0


@pytest.mark.asyncio
async def test_guild_isolation_in_list_games(db, game_a, game_b, guild_a_id, guild_b_id):
    """Verify complete guild isolation in list_games across multiple operations."""
    from services.api.services.games import GameService
    from shared.messaging.publisher import EventPublisher

    service = GameService(
        db=db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    await db.commit()

    # Guild A listing
    games_a, total_a = await service.list_games(guild_id=guild_a_id)
    assert total_a == 1
    assert all(g.guild_id == guild_a_id for g in games_a)
    assert game_b.id not in [g.id for g in games_a]

    # Guild B listing
    games_b, total_b = await service.list_games(guild_id=guild_b_id)
    assert total_b == 1
    assert all(g.guild_id == guild_b_id for g in games_b)
    assert game_a.id not in [g.id for g in games_b]
