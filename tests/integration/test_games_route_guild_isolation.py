# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Integration tests for games database query patterns before guild_queries migration.

These tests establish behavioral baseline for GameService database operations.
Focus: Verify current database query behavior with minimal mocking.

IMPORTANT: Many tests document CURRENT INSECURE BEHAVIOR (no guild filtering in get_game).
After migration to guild_queries wrappers, tests must be updated to verify enforcement.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text

from services.api.services.games import GameService
from shared.messaging.publisher import EventPublisher
from shared.models import GameStatus
from shared.models.game import GameSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("db_fixture", "guild_context", "expected_games"),
    [
        ("admin_db", None, ["game_a", "game_b"]),  # Admin sees all
        ("app_db", "guild_a", ["game_a"]),  # Guild A context sees only game A
        ("app_db", "guild_b", ["game_b"]),  # Guild B context sees only game B
        ("app_db", None, []),  # No guild context sees nothing (RLS blocks all)
    ],
)
async def test_get_game_with_different_database_sessions(
    request,
    admin_db,
    app_db,
    test_game_environment,
    db_fixture,
    guild_context,
    expected_games,
):
    """Verify get_game respects RLS guild filtering based on database session and context.

    Tests that:
    - admin_db (BYPASSRLS) sees all games regardless of guild
    - app_db with guild context sees only games from that guild
    - app_db without guild context sees no games (RLS blocks all)

    This validates that RLS is working correctly and admin bypass is expected behavior,
    not a security flaw.
    """
    # Create test data for two guilds using composite fixture
    env_a = test_game_environment(title="Game A")
    env_b = test_game_environment(title="Game B")

    guild_a = env_a["guild"]
    game_a = env_a["game"]
    guild_b = env_b["guild"]
    game_b = env_b["game"]

    # Get the appropriate database session for this test case
    db_session = request.getfixturevalue(db_fixture)

    # Set guild context if specified
    if guild_context:
        guild_id = guild_a["id"] if guild_context == "guild_a" else guild_b["id"]
        await db_session.execute(
            text("SELECT set_config('app.current_guild_ids', :guild_ids, false)"),
            {"guild_ids": guild_id},
        )

    service = GameService(
        db=db_session,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
        channel_resolver=MagicMock(),
    )

    # Test game A
    result_a = await service.get_game(game_a["id"])
    if "game_a" in expected_games:
        assert result_a is not None, (
            f"Expected game A to be visible with {db_fixture}/{guild_context}"
        )
        assert result_a.id == game_a["id"]
    else:
        assert result_a is None, f"Expected game A to be filtered with {db_fixture}/{guild_context}"

    # Test game B
    result_b = await service.get_game(game_b["id"])
    if "game_b" in expected_games:
        assert result_b is not None, (
            f"Expected game B to be visible with {db_fixture}/{guild_context}"
        )
        assert result_b.id == game_b["id"]
    else:
        assert result_b is None, f"Expected game B to be filtered with {db_fixture}/{guild_context}"


@pytest.mark.asyncio
async def test_list_games_filters_by_guild_when_specified(admin_db, test_game_environment):
    """Verify list_games correctly filters by guild_id when parameter provided."""
    # Create test data for two guilds
    env_a = test_game_environment(title="Game A")
    env_b = test_game_environment(title="Game B")

    guild_a = env_a["guild"]
    game_a = env_a["game"]
    guild_b = env_b["guild"]
    game_b = env_b["game"]

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
        channel_resolver=MagicMock(),
    )

    await admin_db.commit()

    # List games for guild A
    games_a, total_a = await service.list_games(guild_id=guild_a["id"])
    assert total_a == 1
    assert len(games_a) == 1
    assert games_a[0].id == game_a["id"]
    assert games_a[0].guild_id == guild_a["id"]

    # List games for guild B
    games_b, total_b = await service.list_games(guild_id=guild_b["id"])
    assert total_b == 1
    assert len(games_b) == 1
    assert games_b[0].id == game_b["id"]
    assert games_b[0].guild_id == guild_b["id"]


@pytest.mark.asyncio
async def test_list_games_with_channel_filter(admin_db, test_game_environment):
    """Verify list_games respects channel filter within guild."""
    env = test_game_environment()
    guild = env["guild"]
    channel = env["channel"]
    game = env["game"]

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
        channel_resolver=MagicMock(),
    )

    await admin_db.commit()

    games, total = await service.list_games(guild_id=guild["id"], channel_id=channel["id"])
    assert total == 1
    assert len(games) == 1
    assert games[0].id == game["id"]
    assert games[0].channel_id == channel["id"]


@pytest.mark.asyncio
async def test_list_games_with_status_filter(admin_db, test_environment):
    """Verify list_games respects status filter."""
    env = test_environment()
    guild = env["guild"]
    channel = env["channel"]
    user = env["user"]

    # Create game directly in async session
    game = GameSession(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=user["id"],
        title="Test Game",
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        max_players=4,
        status=GameStatus.SCHEDULED,
    )
    admin_db.add(game)
    await admin_db.commit()
    await admin_db.refresh(game)

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
        channel_resolver=MagicMock(),
    )

    # List scheduled games - should find the game we created
    games, total = await service.list_games(guild_id=guild["id"], status="SCHEDULED")
    assert total == 1
    assert games[0].id == game.id
    assert games[0].status == GameStatus.SCHEDULED

    # List completed games (should be empty)
    games_completed, total_completed = await service.list_games(
        guild_id=guild["id"], status="COMPLETED"
    )
    assert total_completed == 0
    assert len(games_completed) == 0


@pytest.mark.asyncio
async def test_list_games_pagination(admin_db, test_environment, create_template):
    """Verify list_games pagination works correctly."""
    env = test_environment()
    guild = env["guild"]
    channel = env["channel"]
    user = env["user"]
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    # Create multiple games
    for i in range(5):
        game = GameSession(
            guild_id=guild["id"],
            channel_id=channel["id"],
            template_id=template["id"],
            host_id=user["id"],
            title=f"Game {i}",
            scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=i + 1),
            max_players=4,
            status=GameStatus.SCHEDULED,
        )
        admin_db.add(game)

    await admin_db.commit()

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
        channel_resolver=MagicMock(),
    )

    # Get first page
    games_page1, total = await service.list_games(guild_id=guild["id"], limit=2, offset=0)
    assert total == 5
    assert len(games_page1) == 2

    # Get second page
    games_page2, total = await service.list_games(guild_id=guild["id"], limit=2, offset=2)
    assert total == 5
    assert len(games_page2) == 2

    # Verify different games on each page
    page1_ids = {g.id for g in games_page1}
    page2_ids = {g.id for g in games_page2}
    assert len(page1_ids & page2_ids) == 0


@pytest.mark.asyncio
async def test_guild_isolation_in_list_games(admin_db, test_game_environment):
    """Verify complete guild isolation in list_games across multiple operations."""
    # Create test data for two guilds
    env_a = test_game_environment(title="Game A")
    env_b = test_game_environment(title="Game B")

    guild_a = env_a["guild"]
    game_a = env_a["game"]
    guild_b = env_b["guild"]
    game_b = env_b["game"]

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
        channel_resolver=MagicMock(),
    )

    await admin_db.commit()

    # Guild A listing
    games_a, total_a = await service.list_games(guild_id=guild_a["id"])
    assert total_a == 1
    assert all(g.guild_id == guild_a["id"] for g in games_a)
    assert game_b["id"] not in [g.id for g in games_a]

    # Guild B listing
    games_b, total_b = await service.list_games(guild_id=guild_b["id"])
    assert total_b == 1
    assert all(g.guild_id == guild_b["id"] for g in games_b)
    assert game_a["id"] not in [g.id for g in games_b]
