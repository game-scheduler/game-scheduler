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


"""Integration tests for GameService image handling.

Tests verify that GameService.create_game(), update_game(), and delete_game()
properly integrate with the image storage service for storing, updating, and
cleaning up images with reference counting.
"""

import datetime
import hashlib
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from services.api.services.games import GameService
from shared.models.game_image import GameImage
from shared.models.user import User
from shared.schemas.auth import CurrentUser
from shared.schemas.game import GameCreateRequest, GameUpdateRequest

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher for GameService."""
    publisher = AsyncMock()
    publisher.publish_deferred = Mock()  # Sync method, not async
    return publisher


@pytest.fixture
def mock_participant_resolver():
    """Mock participant resolver for GameService."""
    resolver = AsyncMock()
    resolver.resolve_initial_participants = AsyncMock(return_value=([], []))
    return resolver


@pytest.fixture
def mock_oauth2_get_user_guilds():
    """
    Override autouse mock to allow real Redis integration in these tests.

    Integration tests should use real Redis cache, not mocks.
    This fixture overrides the autouse fixture from conftest.py by simply
    not applying any patch, allowing the real oauth2.get_user_guilds to run.
    """
    # No patching - let the real implementation run
    return


@pytest.fixture
def valid_png_data() -> bytes:
    """Valid minimal PNG data for testing."""
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def valid_jpeg_data() -> bytes:
    """Valid minimal JPEG data for testing."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xd2"
        b"\xff\xd9"
    )


@pytest.mark.asyncio
async def test_create_game_with_thumbnail_stores_image(
    admin_db: AsyncSession,
    mock_discord_api_client,
    mock_event_publisher,
    mock_participant_resolver,
    create_guild,
    create_channel,
    create_template,
    create_user,
    seed_redis_cache,
    valid_png_data: bytes,
) -> None:
    """GameService.create_game() with thumbnail_data stores image in game_images table."""
    # Setup: Create infrastructure with proper roles
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    user = create_user()

    # Setup Redis cache for authorization
    await seed_redis_cache(
        user_discord_id=user["discord_id"],
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],  # No special roles needed for host
    )

    # Mock Discord API to return empty roles (user can host without special roles)

    service = GameService(
        db=admin_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_api_client,
        participant_resolver=mock_participant_resolver,
    )

    game_data = GameCreateRequest(
        title="Test Game with Thumbnail",
        description="Testing thumbnail storage",
        scheduled_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1),
        template_id=template["id"],
    )

    game = await service.create_game(
        game_data=game_data,
        host_user_id=user["id"],
        access_token="valid-test-token",
        thumbnail_data=valid_png_data,
        thumbnail_mime_type="image/png",
    )
    await admin_db.commit()

    # Game should have thumbnail_id set
    assert game.thumbnail_id is not None
    assert game.banner_image_id is None

    # Image should exist in game_images table
    result = await admin_db.execute(select(GameImage).where(GameImage.id == game.thumbnail_id))
    image = result.scalar_one()

    assert image.image_data == valid_png_data
    assert image.mime_type == "image/png"
    assert image.reference_count == 1
    assert image.content_hash == hashlib.sha256(valid_png_data).hexdigest()


@pytest.mark.asyncio
async def test_create_game_with_both_images_stores_both(
    admin_db: AsyncSession,
    mock_discord_api_client,
    mock_event_publisher,
    mock_participant_resolver,
    create_guild,
    create_channel,
    create_template,
    create_user,
    seed_redis_cache,
    valid_png_data: bytes,
    valid_jpeg_data: bytes,
) -> None:
    """GameService.create_game() with both images stores thumbnail and banner."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    user = create_user()

    await seed_redis_cache(
        user_discord_id=user["discord_id"],
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],
    )

    service = GameService(
        db=admin_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_api_client,
        participant_resolver=mock_participant_resolver,
    )

    game_data = GameCreateRequest(
        title="Test Game with Both Images",
        description="Testing both images",
        scheduled_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1),
        template_id=template["id"],
    )

    game = await service.create_game(
        game_data=game_data,
        host_user_id=user["id"],
        access_token="valid-test-token",
        thumbnail_data=valid_png_data,
        thumbnail_mime_type="image/png",
        image_data=valid_jpeg_data,
        image_mime_type="image/jpeg",
    )
    await admin_db.commit()

    assert game.thumbnail_id is not None
    assert game.banner_image_id is not None

    # Both images should exist
    thumb_result = await admin_db.execute(
        select(GameImage).where(GameImage.id == game.thumbnail_id)
    )
    thumb = thumb_result.scalar_one()
    assert thumb.mime_type == "image/png"
    assert thumb.reference_count == 1

    banner_result = await admin_db.execute(
        select(GameImage).where(GameImage.id == game.banner_image_id)
    )
    banner = banner_result.scalar_one()
    assert banner.mime_type == "image/jpeg"
    assert banner.reference_count == 1


@pytest.mark.asyncio
async def test_create_two_games_same_image_deduplicates(
    admin_db: AsyncSession,
    mock_discord_api_client,
    mock_event_publisher,
    mock_participant_resolver,
    create_guild,
    create_channel,
    create_template,
    create_user,
    seed_redis_cache,
    valid_png_data: bytes,
) -> None:
    """Creating two games with identical image data reuses same image record."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    user = create_user()

    await seed_redis_cache(
        user_discord_id=user["discord_id"],
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],
    )

    service = GameService(
        db=admin_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_api_client,
        participant_resolver=mock_participant_resolver,
    )

    # Create first game with image
    game1_data = GameCreateRequest(
        title="Game 1",
        description="First game",
        scheduled_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1),
        template_id=template["id"],
    )

    game1 = await service.create_game(
        game_data=game1_data,
        host_user_id=user["id"],
        access_token="valid-test-token",
        thumbnail_data=valid_png_data,
        thumbnail_mime_type="image/png",
    )
    await admin_db.commit()

    image_id = game1.thumbnail_id

    # Create second game with SAME image data
    game2_data = GameCreateRequest(
        title="Game 2",
        description="Second game",
        scheduled_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=2),
        template_id=template["id"],
    )

    game2 = await service.create_game(
        game_data=game2_data,
        host_user_id=user["id"],
        access_token="valid-test-token",
        thumbnail_data=valid_png_data,
        thumbnail_mime_type="image/png",
    )
    await admin_db.commit()

    # Both games should reference the SAME image
    assert game2.thumbnail_id == image_id

    # Image reference count should be 2
    result = await admin_db.execute(select(GameImage).where(GameImage.id == image_id))
    image = result.scalar_one()
    assert image.reference_count == 2


@pytest.mark.asyncio
async def test_update_game_replaces_thumbnail(
    admin_db: AsyncSession,
    mock_discord_api_client,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    create_guild,
    create_channel,
    create_template,
    create_user,
    seed_redis_cache,
    valid_png_data: bytes,
    valid_jpeg_data: bytes,
) -> None:
    """GameService.update_game() with new thumbnail releases old and stores new."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    user = create_user()

    await seed_redis_cache(
        user_discord_id=user["discord_id"],
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],
        session_token="test-session",
        session_user_id=user["id"],
        session_access_token="valid-test-token",
    )

    service = GameService(
        db=admin_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_api_client,
        participant_resolver=mock_participant_resolver,
    )

    # Create game with PNG thumbnail
    game_data = GameCreateRequest(
        title="Test Game",
        description="Testing update",
        scheduled_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1),
        template_id=template["id"],
    )

    game = await service.create_game(
        game_data=game_data,
        host_user_id=user["id"],
        access_token="valid-test-token",
        thumbnail_data=valid_png_data,
        thumbnail_mime_type="image/png",
    )
    await admin_db.commit()

    old_thumbnail_id = game.thumbnail_id

    # Update game with JPEG thumbnail
    # Get user model from database
    user_result = await admin_db.execute(select(User).where(User.id == user["id"]))
    user_model = user_result.scalar_one()

    current_user = CurrentUser(
        user=user_model,
        access_token="valid-test-token",
        session_token="test-session",
    )

    update_data = GameUpdateRequest(title="Updated Game")

    game = await service.update_game(
        game_id=game.id,
        update_data=update_data,
        current_user=current_user,
        role_service=mock_role_service,
        thumbnail_data=valid_jpeg_data,
        thumbnail_mime_type="image/jpeg",
    )
    await admin_db.commit()

    # New thumbnail should be different
    assert game.thumbnail_id != old_thumbnail_id

    # Old image should be deleted (ref count was 1)
    old_result = await admin_db.execute(select(GameImage).where(GameImage.id == old_thumbnail_id))
    old_image = old_result.scalar_one_or_none()
    assert old_image is None

    # New image should exist
    new_result = await admin_db.execute(select(GameImage).where(GameImage.id == game.thumbnail_id))
    new_image = new_result.scalar_one()
    assert new_image.mime_type == "image/jpeg"
    assert new_image.reference_count == 1


@pytest.mark.asyncio
async def test_delete_game_releases_images(
    admin_db: AsyncSession,
    mock_discord_api_client,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    create_guild,
    create_channel,
    create_template,
    create_user,
    seed_redis_cache,
    valid_png_data: bytes,
) -> None:
    """GameService.delete_game() releases image references and deletes unused images."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    user = create_user()

    await seed_redis_cache(
        user_discord_id=user["discord_id"],
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],
        session_token="test-session",
        session_user_id=user["id"],
        session_access_token="valid-test-token",
    )

    service = GameService(
        db=admin_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_api_client,
        participant_resolver=mock_participant_resolver,
    )

    # Create game with thumbnail
    game_data = GameCreateRequest(
        title="Test Game",
        description="Testing delete",
        scheduled_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1),
        template_id=template["id"],
    )

    game = await service.create_game(
        game_data=game_data,
        host_user_id=user["id"],
        access_token="valid-test-token",
        thumbnail_data=valid_png_data,
        thumbnail_mime_type="image/png",
    )
    await admin_db.commit()

    thumbnail_id = game.thumbnail_id

    # Delete game
    # Get user model from database
    user_result = await admin_db.execute(select(User).where(User.id == user["id"]))
    user_model = user_result.scalar_one()

    current_user = CurrentUser(
        user=user_model,
        access_token="valid-test-token",
        session_token="test-session",
    )

    await service.delete_game(
        game_id=game.id,
        current_user=current_user,
        role_service=mock_role_service,
    )
    await admin_db.commit()

    # Image should be deleted (no more references)
    result = await admin_db.execute(select(GameImage).where(GameImage.id == thumbnail_id))
    image = result.scalar_one_or_none()
    assert image is None


@pytest.mark.asyncio
async def test_delete_shared_image_keeps_image_until_all_refs_gone(
    admin_db: AsyncSession,
    mock_discord_api_client,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    create_guild,
    create_channel,
    create_template,
    create_user,
    seed_redis_cache,
    valid_png_data: bytes,
) -> None:
    """Deleting game with shared image keeps image until all references gone."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    user = create_user()

    await seed_redis_cache(
        user_discord_id=user["discord_id"],
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],
        session_token="test-session",
        session_user_id=user["id"],
        session_access_token="valid-test-token",
    )

    service = GameService(
        db=admin_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_api_client,
        participant_resolver=mock_participant_resolver,
    )

    # Create two games with same image
    game1_data = GameCreateRequest(
        title="Game 1",
        description="First game",
        scheduled_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1),
        template_id=template["id"],
    )

    game1 = await service.create_game(
        game_data=game1_data,
        host_user_id=user["id"],
        access_token="valid-test-token",
        thumbnail_data=valid_png_data,
        thumbnail_mime_type="image/png",
    )
    await admin_db.commit()

    image_id = game1.thumbnail_id

    game2_data = GameCreateRequest(
        title="Game 2",
        description="Second game",
        scheduled_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=2),
        template_id=template["id"],
    )

    game2 = await service.create_game(
        game_data=game2_data,
        host_user_id=user["id"],
        access_token="valid-test-token",
        thumbnail_data=valid_png_data,
        thumbnail_mime_type="image/png",
    )
    await admin_db.commit()

    # Get user model from database
    user_result = await admin_db.execute(select(User).where(User.id == user["id"]))
    user_model = user_result.scalar_one()

    current_user = CurrentUser(
        user=user_model,
        access_token="valid-test-token",
        session_token="test-session",
    )

    # Delete first game
    await service.delete_game(
        game_id=game1.id,
        current_user=current_user,
        role_service=mock_role_service,
    )
    await admin_db.commit()

    # Image should STILL exist (game2 references it)
    result = await admin_db.execute(select(GameImage).where(GameImage.id == image_id))
    image = result.scalar_one()
    assert image.reference_count == 1

    # Delete second game
    await service.delete_game(
        game_id=game2.id,
        current_user=current_user,
        role_service=mock_role_service,
    )
    await admin_db.commit()

    # NOW image should be deleted
    result = await admin_db.execute(select(GameImage).where(GameImage.id == image_id))
    image = result.scalar_one_or_none()
    assert image is None
