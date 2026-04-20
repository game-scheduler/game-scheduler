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


"""Unit tests for participant resolver service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.services import participant_resolver as resolver_module
from shared.models import user as user_model


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def resolver():
    """Create participant resolver instance."""
    return resolver_module.ParticipantResolver()


@pytest.mark.asyncio
async def test_resolve_placeholder_strings(resolver):
    """Test that placeholder strings (non-@mentions) are always valid."""
    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=["Alice", "Bob", "Charlie"],
    )

    assert len(valid) == 3
    assert len(errors) == 0
    assert all(p["type"] == "placeholder" for p in valid)
    assert valid[0]["display_name"] == "Alice"
    assert valid[1]["display_name"] == "Bob"
    assert valid[2]["display_name"] == "Charlie"


@pytest.mark.asyncio
async def test_resolve_single_match(resolver):
    """Test @mention with single member match."""
    members = [
        {
            "uid": "987654321",
            "username": "testuser",
            "global_name": "Test User",
            "nick": None,
            "roles": [],
            "avatar_url": None,
        }
    ]
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=members,
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=["@testuser"],
        )

    assert len(valid) == 1
    assert len(errors) == 0
    assert valid[0]["type"] == "discord"
    assert valid[0]["discord_id"] == "987654321"


@pytest.mark.asyncio
async def test_resolve_multiple_matches(resolver):
    """Test @mention with multiple member matches returns disambiguation."""
    members = [
        {
            "uid": "111",
            "username": "alice1",
            "global_name": "Alice One",
            "nick": None,
            "roles": [],
            "avatar_url": None,
        },
        {
            "uid": "222",
            "username": "alice2",
            "global_name": "Alice Two",
            "nick": "Alice",
            "roles": [],
            "avatar_url": None,
        },
    ]
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=members,
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=["@alice"],
        )

    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0]["input"] == "@alice"
    assert errors[0]["reason"] == "Multiple matches found"
    assert len(errors[0]["suggestions"]) == 2
    assert errors[0]["suggestions"][0]["discordId"] == "111"
    assert errors[0]["suggestions"][1]["displayName"] == "Alice"


@pytest.mark.asyncio
async def test_resolve_no_match(resolver):
    """Test @mention with no member matches returns error."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=["@nonexistent"],
        )

    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0]["input"] == "@nonexistent"
    assert errors[0]["reason"] == "User not found in server"
    assert errors[0]["suggestions"] == []


@pytest.mark.asyncio
async def test_resolve_mixed_participants(resolver):
    """Test resolving mix of @mentions and placeholders."""
    members = [
        {
            "uid": "111",
            "username": "validuser",
            "global_name": "Valid User",
            "nick": None,
            "roles": [],
            "avatar_url": None,
        }
    ]
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=members,
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=["@validuser", "PlaceholderName"],
        )

    assert len(valid) == 2
    assert len(errors) == 0
    assert valid[0]["type"] == "discord"
    assert valid[0]["discord_id"] == "111"
    assert valid[1]["type"] == "placeholder"
    assert valid[1]["display_name"] == "PlaceholderName"


@pytest.mark.asyncio
async def test_resolve_empty_input(resolver):
    """Test that empty strings are filtered out."""
    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=["Alice", "", "  ", "Bob"],
    )

    assert len(valid) == 2
    assert len(errors) == 0
    assert valid[0]["display_name"] == "Alice"
    assert valid[1]["display_name"] == "Bob"


@pytest.mark.asyncio
async def test_ensure_user_exists_creates_new(resolver, mock_db):
    """Test ensure_user_exists creates new user if not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()

    user = await resolver.ensure_user_exists(mock_db, "999")

    assert isinstance(user, user_model.User)
    assert user.discord_id == "999"
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_user_exists_returns_existing(resolver, mock_db):
    """Test ensure_user_exists returns existing user."""
    existing_user = user_model.User(discord_id="888")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    user = await resolver.ensure_user_exists(mock_db, "888")

    assert user is existing_user
    mock_db.add.assert_not_called()
    mock_db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_discord_api_error_handling(resolver):
    """Test handling of errors from the member search projection."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            side_effect=Exception("Redis connection error"),
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=["@testuser"],
        )

    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0]["input"] == "@testuser"
    assert "error" in errors[0]["reason"].lower()
    assert errors[0]["suggestions"] == []


@pytest.mark.asyncio
async def test_network_error_handling(resolver):
    """Test handling of errors during member search."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            side_effect=Exception("Network connection failed"),
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=["@testuser"],
        )

    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0]["input"] == "@testuser"
    assert "error" in errors[0]["reason"].lower()
    assert errors[0]["suggestions"] == []


@pytest.mark.asyncio
async def test_malformed_response_handling(resolver):
    """Test handling of malformed projection data (missing uid key)."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            side_effect=KeyError("uid"),
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=["@testuser"],
        )

    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0]["input"] == "@testuser"
    assert "error" in errors[0]["reason"].lower()


@pytest.mark.asyncio
async def test_resolve_discord_mention_format(resolver):
    """Test resolving Discord internal mention format <@discord_id>."""
    member_data = {
        "username": "testuser",
        "global_name": "Test User",
        "nick": None,
    }
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            return_value=member_data,
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=["<@987654321012345678>"],
        )

    assert len(valid) == 1
    assert len(errors) == 0
    assert valid[0]["type"] == "discord"
    assert valid[0]["discord_id"] == "987654321012345678"
    assert valid[0]["original_input"] == "<@987654321012345678>"


@pytest.mark.asyncio
async def test_resolve_mixed_mention_formats(resolver):
    """Test resolving mix of @username and <@discord_id> formats."""
    search_members = [
        {
            "uid": "111222333444555666",
            "username": "testuser",
            "global_name": "Test User",
            "nick": None,
            "roles": [],
            "avatar_url": None,
        }
    ]
    member_data = {
        "username": "mentionuser",
        "global_name": "Mention User",
        "nick": None,
    }
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=search_members,
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            return_value=member_data,
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=[
                "@testuser",
                "<@987654321012345678>",
                "PlaceholderName",
            ],
        )

    assert len(valid) == 3
    assert len(errors) == 0
    assert valid[0]["type"] == "discord"
    assert valid[0]["discord_id"] == "111222333444555666"
    assert valid[1]["type"] == "discord"
    assert valid[1]["discord_id"] == "987654321012345678"
    assert valid[2]["type"] == "placeholder"
    assert valid[2]["display_name"] == "PlaceholderName"


@pytest.mark.asyncio
async def test_reject_invalid_discord_mention_format(resolver):
    """Test that invalid Discord mention formats are treated as placeholders."""
    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=[
            "<@123>",  # Too short - treated as placeholder
            "<@abcdef>",  # Not numeric - treated as placeholder
            "<@12345678901234567890123>",  # Too long - treated as placeholder
        ],
    )

    assert len(valid) == 3
    assert len(errors) == 0
    # All invalid Discord mention formats should be treated as placeholders
    assert all(p["type"] == "placeholder" for p in valid)
    assert valid[0]["display_name"] == "<@123>"
    assert valid[1]["display_name"] == "<@abcdef>"
    assert valid[2]["display_name"] == "<@12345678901234567890123>"


@pytest.mark.asyncio
async def test_discord_mention_format_with_whitespace(resolver):
    """Test Discord mention format handles whitespace correctly."""
    member_data = {
        "username": "testuser",
        "global_name": "Test User",
        "nick": None,
    }
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            return_value=member_data,
        ),
    ):
        valid, errors = await resolver.resolve_initial_participants(
            guild_discord_id="123456789",
            participant_inputs=[
                "  <@987654321012345678>  ",  # Leading/trailing spaces
            ],
        )

    assert len(valid) == 1
    assert len(errors) == 0
    assert valid[0]["type"] == "discord"
    assert valid[0]["discord_id"] == "987654321012345678"


# Unit tests for extracted helper methods


@pytest.mark.asyncio
async def test_resolve_discord_mention_format_success(resolver):
    """Test _resolve_discord_mention_format with successful member fetch."""
    member_data = {
        "username": "testuser",
        "global_name": "Test User",
        "nick": "TestNick",
    }
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            return_value=member_data,
        ),
    ):
        participant, error = await resolver._resolve_discord_mention_format(
            guild_discord_id="999",
            input_text="<@123456789012345678>",
            discord_id="123456789012345678",
        )

    assert participant is not None
    assert error is None
    assert participant["type"] == "discord"
    assert participant["discord_id"] == "123456789012345678"
    assert participant["username"] == "testuser"
    assert participant["display_name"] == "TestNick"
    assert participant["original_input"] == "<@123456789012345678>"


@pytest.mark.asyncio
async def test_resolve_discord_mention_format_no_nick(resolver):
    """Test _resolve_discord_mention_format falls back to global_name when no nick."""
    member_data = {
        "username": "testuser",
        "global_name": "Test User",
        "nick": None,
    }
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            return_value=member_data,
        ),
    ):
        participant, error = await resolver._resolve_discord_mention_format(
            guild_discord_id="999",
            input_text="<@123456789012345678>",
            discord_id="123456789012345678",
        )

    assert participant["display_name"] == "Test User"


@pytest.mark.asyncio
async def test_resolve_discord_mention_format_no_global_name(resolver):
    """Test _resolve_discord_mention_format falls back to username when no nick or global_name."""
    member_data = {
        "username": "testuser",
        "global_name": None,
        "nick": None,
    }
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            return_value=member_data,
        ),
    ):
        participant, error = await resolver._resolve_discord_mention_format(
            guild_discord_id="999",
            input_text="<@123456789012345678>",
            discord_id="123456789012345678",
        )

    assert participant["display_name"] == "testuser"


@pytest.mark.asyncio
async def test_resolve_discord_mention_format_not_found(resolver):
    """Test _resolve_discord_mention_format handles member absent from projection."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        participant, error = await resolver._resolve_discord_mention_format(
            guild_discord_id="999",
            input_text="<@123456789012345678>",
            discord_id="123456789012345678",
        )

    assert participant is None
    assert error is not None
    assert error["input"] == "<@123456789012345678>"
    assert error["reason"] == "User not found in server"
    assert error["suggestions"] == []


@pytest.mark.asyncio
async def test_resolve_discord_mention_format_api_error(resolver):
    """Test _resolve_discord_mention_format handles unexpected error."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Redis unavailable"),
        ),
    ):
        participant, error = await resolver._resolve_discord_mention_format(
            guild_discord_id="999",
            input_text="<@123456789012345678>",
            discord_id="123456789012345678",
        )

    assert participant is None
    assert error is not None
    assert error["reason"] == "Internal error fetching user"


@pytest.mark.asyncio
async def test_resolve_discord_mention_format_unexpected_error(resolver):
    """Test _resolve_discord_mention_format handles unexpected exception from projection."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected error"),
        ),
    ):
        participant, error = await resolver._resolve_discord_mention_format(
            guild_discord_id="999",
            input_text="<@123456789012345678>",
            discord_id="123456789012345678",
        )

    assert participant is None
    assert error is not None
    assert error["reason"] == "Internal error fetching user"


@pytest.mark.asyncio
async def test_resolve_user_friendly_mention_single_match(resolver):
    """Test _resolve_user_friendly_mention with single match."""
    members = [
        {
            "uid": "111222333",
            "username": "alice",
            "global_name": "Alice",
            "nick": None,
            "roles": [],
            "avatar_url": None,
        }
    ]
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=members,
        ),
    ):
        participant, error = await resolver._resolve_user_friendly_mention(
            guild_discord_id="999",
            input_text="@alice",
            mention_text="alice",
        )

    assert participant is not None
    assert error is None
    assert participant["type"] == "discord"
    assert participant["discord_id"] == "111222333"
    assert participant["original_input"] == "@alice"


@pytest.mark.asyncio
async def test_resolve_user_friendly_mention_no_match(resolver):
    """Test _resolve_user_friendly_mention with no matches."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        participant, error = await resolver._resolve_user_friendly_mention(
            guild_discord_id="999",
            input_text="@nobody",
            mention_text="nobody",
        )

    assert participant is None
    assert error is not None
    assert error["input"] == "@nobody"
    assert error["reason"] == "User not found in server"
    assert error["suggestions"] == []


@pytest.mark.asyncio
async def test_resolve_user_friendly_mention_multiple_matches(resolver):
    """Test _resolve_user_friendly_mention with multiple matches."""
    members = [
        {
            "uid": "111",
            "username": "alice1",
            "global_name": "Alice One",
            "nick": None,
            "roles": [],
            "avatar_url": None,
        },
        {
            "uid": "222",
            "username": "alice2",
            "global_name": "Alice Two",
            "nick": "Alice",
            "roles": [],
            "avatar_url": None,
        },
        {
            "uid": "333",
            "username": "alice3",
            "global_name": None,
            "nick": None,
            "roles": [],
            "avatar_url": None,
        },
    ]
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=members,
        ),
    ):
        participant, error = await resolver._resolve_user_friendly_mention(
            guild_discord_id="999",
            input_text="@alice",
            mention_text="alice",
        )

    assert participant is None
    assert error is not None
    assert error["input"] == "@alice"
    assert error["reason"] == "Multiple matches found"
    assert len(error["suggestions"]) == 3
    assert error["suggestions"][0]["discordId"] == "111"
    assert error["suggestions"][1]["displayName"] == "Alice"
    assert error["suggestions"][2]["displayName"] == "alice3"


@pytest.mark.asyncio
async def test_resolve_user_friendly_mention_api_error(resolver):
    """Test _resolve_user_friendly_mention handles exception from search."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            side_effect=Exception("Redis error"),
        ),
    ):
        participant, error = await resolver._resolve_user_friendly_mention(
            guild_discord_id="999",
            input_text="@test",
            mention_text="test",
        )

    assert participant is None
    assert error is not None
    assert "error" in error["reason"].lower()


@pytest.mark.asyncio
async def test_resolve_user_friendly_mention_unexpected_error(resolver):
    """Test _resolve_user_friendly_mention handles unexpected exception."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Boom"),
        ),
    ):
        participant, error = await resolver._resolve_user_friendly_mention(
            guild_discord_id="999",
            input_text="@test",
            mention_text="test",
        )

    assert participant is None
    assert error is not None
    assert error["reason"] == "Internal error searching for user"


def test_create_placeholder_participant(resolver):
    """Test _create_placeholder_participant creates correct structure."""
    participant = resolver._create_placeholder_participant("Player One")

    assert participant["type"] == "placeholder"
    assert participant["display_name"] == "Player One"
    assert participant["original_input"] == "Player One"


def test_create_placeholder_participant_special_chars(resolver):
    """Test _create_placeholder_participant handles special characters."""
    participant = resolver._create_placeholder_participant("Player #1 (Team A)")

    assert participant["type"] == "placeholder"
    assert participant["display_name"] == "Player #1 (Team A)"
    assert participant["original_input"] == "Player #1 (Team A)"


@pytest.mark.asyncio
async def test_process_single_participant_input_discord_mention(resolver):
    """Test _process_single_participant_input with Discord mention format."""
    member_data = {
        "username": "testuser",
        "global_name": "Test User",
        "nick": "TestNick",
    }
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            return_value=member_data,
        ),
    ):
        participant, error = await resolver._process_single_participant_input(
            guild_discord_id="999",
            input_text="<@12345678901234567>",
        )

    assert participant is not None
    assert participant["type"] == "discord"
    assert participant["discord_id"] == "12345678901234567"
    assert error is None


@pytest.mark.asyncio
async def test_process_single_participant_input_user_friendly_mention(resolver):
    """Test _process_single_participant_input with @username format."""
    members = [
        {
            "uid": "987654321",
            "username": "testuser",
            "global_name": None,
            "nick": None,
            "roles": [],
            "avatar_url": None,
        }
    ]
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=members,
        ),
    ):
        participant, error = await resolver._process_single_participant_input(
            guild_discord_id="999",
            input_text="@testuser",
        )

    assert participant is not None
    assert participant["type"] == "discord"
    assert participant["discord_id"] == "987654321"
    assert error is None


@pytest.mark.asyncio
async def test_process_single_participant_input_placeholder(resolver):
    """Test _process_single_participant_input with placeholder string."""
    participant, error = await resolver._process_single_participant_input(
        guild_discord_id="999",
        input_text="Player One",
    )

    assert participant is not None
    assert participant["type"] == "placeholder"
    assert participant["display_name"] == "Player One"
    assert error is None


@pytest.mark.asyncio
async def test_process_single_participant_input_empty_string(resolver):
    """Test _process_single_participant_input with empty string."""
    participant, error = await resolver._process_single_participant_input(
        guild_discord_id="999",
        input_text="",
    )

    assert participant is None
    assert error is None


@pytest.mark.asyncio
async def test_process_single_participant_input_whitespace_only(resolver):
    """Test _process_single_participant_input with whitespace-only string."""
    participant, error = await resolver._process_single_participant_input(
        guild_discord_id="999",
        input_text="   ",
    )

    assert participant is None
    assert error is None


@pytest.mark.asyncio
async def test_process_single_participant_input_discord_mention_not_found(resolver):
    """Test _process_single_participant_input when Discord user not found."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.get_member",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        participant, error = await resolver._process_single_participant_input(
            guild_discord_id="999",
            input_text="<@12345678901234567>",
        )

    assert participant is None
    assert error is not None
    assert error["input"] == "<@12345678901234567>"


@pytest.mark.asyncio
async def test_process_single_participant_input_user_friendly_mention_not_found(resolver):
    """Test _process_single_participant_input when @username not found."""
    with (
        patch(
            "services.api.services.participant_resolver.cache_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ),
        patch(
            "services.api.services.participant_resolver.member_projection.search_members_by_prefix",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        participant, error = await resolver._process_single_participant_input(
            guild_discord_id="999",
            input_text="@unknownuser",
        )

    assert participant is None
    assert error is not None
    assert error["input"] == "@unknownuser"
