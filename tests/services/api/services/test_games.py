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


"""Unit tests for game management service."""

import datetime
import uuid
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.services import participant_resolver as resolver_module
from services.api.services.games import (
    DEFAULT_GAME_DURATION_MINUTES,
    GameMediaAttachments,
)
from shared.models import channel as channel_model
from shared.models import game as game_model
from shared.models import game_status_schedule as game_status_schedule_model
from shared.models import participant as participant_model
from shared.models import template as template_model
from shared.models import user as user_model
from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod
from shared.schemas import game as game_schemas
from shared.schemas.auth import CurrentUser
from shared.utils.games import DEFAULT_MAX_PLAYERS
from shared.utils.participant_sorting import partition_participants


@pytest.fixture
def mock_role_service():
    """Create mock role service."""
    role_service = AsyncMock()
    role_service.check_game_host_permission = AsyncMock(return_value=True)
    return role_service


@pytest.fixture
def sample_template(sample_guild, sample_channel):
    """Create sample game template."""
    template_id = str(uuid.uuid4())
    return template_model.GameTemplate(
        id=template_id,
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        name="Test Template",
        order=0,
        is_default=True,
        allowed_host_role_ids=None,
        max_players=10,
        reminder_minutes=[60, 15],
    )


@pytest.fixture
def sample_game_data(sample_template):
    """Create sample game creation request."""
    return game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        max_players=4,
        reminder_minutes=[60],
    )


def setup_create_game_mocks(
    mock_db,
    sample_template,
    sample_guild,
    sample_user,
    sample_channel,
    created_game,
):
    """
    Set up common mock pattern for game creation tests.

    Creates mock results for the sequence of database queries in create_game:
    1. Template lookup (scalar_one_or_none) - in _load_game_dependencies
    2. Guild lookup (scalar_one_or_none) - in _load_game_dependencies
    3. Channel lookup (scalar_one_or_none) - in _load_game_dependencies
    4. Host user lookup (scalar_one_or_none) - in _resolve_game_host
    5. Game reload with relationships (scalar_one)
    6. Final get_game() call after commit (scalar_one_or_none)
    """
    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template

    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild

    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel

    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = created_game

    # Final get_game() uses scalar_one_or_none(), needs separate mock
    get_game_result = MagicMock()
    get_game_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            host_result,
            reload_result,
            get_game_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    def mock_add_side_effect(obj):
        if isinstance(obj, game_model.GameSession):
            obj.id = created_game.id
            obj.channel_id = created_game.channel_id

    mock_db.add.side_effect = mock_add_side_effect


# Tests for _resolve_template_fields() method


def test_resolve_template_fields_uses_request_values(game_service):
    """Test that request values take precedence over template defaults."""
    template = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        name="Test Template",
        order=0,
        is_default=False,
        max_players=10,
        reminder_minutes=[60, 15],
        expected_duration_minutes=120,
        where="Discord",
        signup_instructions="Template instructions",
        default_signup_method=SignupMethod.HOST_SELECTED.value,
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template.id,
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.datetime.now(UTC),
        max_players=8,
        reminder_minutes=[30],
        expected_duration_minutes=90,
        where="In Person",
        signup_instructions="Custom instructions",
        signup_method=SignupMethod.SELF_SIGNUP.value,
    )

    result = game_service._resolve_template_fields(game_data, template)

    assert result["max_players"] == 8
    assert result["reminder_minutes"] == [30]
    assert result["expected_duration_minutes"] == 90
    assert result["where"] == "In Person"
    assert result["signup_instructions"] == "Custom instructions"
    assert result["signup_method"] == SignupMethod.SELF_SIGNUP.value


def test_resolve_template_fields_uses_template_defaults(game_service):
    """Test that template defaults are used when request values are None."""
    template = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        name="Test Template",
        order=0,
        is_default=False,
        max_players=10,
        reminder_minutes=[60, 15],
        expected_duration_minutes=120,
        where="Discord",
        signup_instructions="Template instructions",
        default_signup_method=SignupMethod.HOST_SELECTED.value,
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template.id,
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.datetime.now(UTC),
    )

    result = game_service._resolve_template_fields(game_data, template)

    assert result["max_players"] == 10
    assert result["reminder_minutes"] == [60, 15]
    assert result["expected_duration_minutes"] == 120
    assert result["where"] == "Discord"
    assert result["signup_instructions"] == "Template instructions"
    assert result["signup_method"] == SignupMethod.HOST_SELECTED.value


def test_resolve_template_fields_handles_empty_string_overrides(game_service):
    """Test that empty strings in request override template defaults."""
    template = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        name="Test Template",
        order=0,
        is_default=False,
        max_players=10,
        where="Discord",
        signup_instructions="Template instructions",
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template.id,
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.datetime.now(UTC),
        where="",
        signup_instructions="",
    )

    result = game_service._resolve_template_fields(game_data, template)

    assert result["where"] == ""
    assert result["signup_instructions"] == ""


def test_resolve_template_fields_uses_default_reminder_when_template_none(game_service):
    """Test that default reminder [60, 15] is used when template has None."""
    template = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        name="Test Template",
        order=0,
        is_default=False,
        max_players=10,
        reminder_minutes=None,
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template.id,
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.datetime.now(UTC),
    )

    result = game_service._resolve_template_fields(game_data, template)

    assert result["reminder_minutes"] == [60, 15]


def test_resolve_template_fields_empty_reminder_list_overrides_template(game_service):
    """Test that empty reminder list in request overrides template defaults."""
    template = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        name="Test Template",
        order=0,
        is_default=False,
        max_players=10,
        reminder_minutes=[60, 15],
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template.id,
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.datetime.now(UTC),
        reminder_minutes=[],
    )

    result = game_service._resolve_template_fields(game_data, template)

    assert result["reminder_minutes"] == []


def test_resolve_template_fields_signup_method_fallback_chain(game_service):
    """Test signup method resolution: request → template → SELF_SIGNUP."""
    template = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        name="Test Template",
        order=0,
        is_default=False,
        max_players=10,
        default_signup_method=None,
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template.id,
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.datetime.now(UTC),
        signup_method=None,
    )

    result = game_service._resolve_template_fields(game_data, template)

    assert result["signup_method"] == SignupMethod.SELF_SIGNUP.value


def test_resolve_template_fields_validates_signup_method_against_allowed_list(
    game_service,
):
    """Test that signup method is validated against template's allowed list."""
    template = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        name="Test Template",
        order=0,
        is_default=False,
        max_players=10,
        allowed_signup_methods=[SignupMethod.HOST_SELECTED.value],
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template.id,
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.datetime.now(UTC),
        signup_method=SignupMethod.SELF_SIGNUP.value,
    )

    with pytest.raises(ValueError, match="not allowed for this template"):
        game_service._resolve_template_fields(game_data, template)


def test_resolve_template_fields_allows_any_method_when_allowed_list_none(game_service):
    """Test that any signup method is allowed when template has no restrictions."""
    template = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        name="Test Template",
        order=0,
        is_default=False,
        max_players=10,
        allowed_signup_methods=None,
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template.id,
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.datetime.now(UTC),
        signup_method=SignupMethod.SELF_SIGNUP.value,
    )

    result = game_service._resolve_template_fields(game_data, template)

    assert result["signup_method"] == SignupMethod.SELF_SIGNUP.value


def test_resolve_template_fields_allows_any_method_when_allowed_list_empty(
    game_service,
):
    """Test that any signup method is allowed when template has empty allowed list."""
    template = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        name="Test Template",
        order=0,
        is_default=False,
        max_players=10,
        allowed_signup_methods=[],
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template.id,
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.datetime.now(UTC),
        signup_method=SignupMethod.SELF_SIGNUP.value,
    )

    result = game_service._resolve_template_fields(game_data, template)

    assert result["signup_method"] == SignupMethod.SELF_SIGNUP.value


# Tests for _resolve_game_host() method


@pytest.mark.asyncio
async def test_resolve_game_host_no_override_uses_requester(
    game_service, mock_db, sample_game_data, sample_guild, sample_user
):
    """Test _resolve_game_host returns requester when no host override specified."""
    sample_game_data.host = None

    # Mock database lookup for requester
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute = AsyncMock(return_value=host_result)

    host_user_id, host_user = await game_service._resolve_game_host(
        sample_game_data, sample_guild, sample_user.id, "token"
    )

    assert host_user_id == sample_user.id
    assert host_user == sample_user


@pytest.mark.asyncio
async def test_resolve_game_host_empty_string_uses_requester(
    game_service, mock_db, sample_game_data, sample_guild, sample_user
):
    """Test _resolve_game_host treats empty string as no override."""
    sample_game_data.host = "  "

    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute = AsyncMock(return_value=host_result)

    host_user_id, host_user = await game_service._resolve_game_host(
        sample_game_data, sample_guild, sample_user.id, "token"
    )

    assert host_user_id == sample_user.id
    assert host_user == sample_user


@pytest.mark.asyncio
async def test_resolve_game_host_requester_not_found_raises_error(
    game_service, mock_db, sample_game_data, sample_guild
):
    """Test _resolve_game_host raises ValueError when requester not found with override."""
    sample_game_data.host = "@someone"
    requester_id = str(uuid.uuid4())

    # Mock requester lookup returning None
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=requester_result)

    with pytest.raises(ValueError, match="Requester user not found"):
        await game_service._resolve_game_host(sample_game_data, sample_guild, requester_id, "token")


@pytest.mark.asyncio
async def test_resolve_game_host_non_bot_manager_cannot_override(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_game_data,
    sample_guild,
    sample_user,
):
    """Test _resolve_game_host raises error when non-bot-manager tries to override."""
    sample_game_data.host = "@otheruser"

    # Mock requester lookup
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute = AsyncMock(return_value=requester_result)

    # Mock role service to deny bot manager permission
    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=False)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(ValueError, match="Only bot managers can specify the game host"):
            await game_service._resolve_game_host(
                sample_game_data, sample_guild, sample_user.id, "token"
            )


@pytest.mark.asyncio
async def test_resolve_game_host_bot_manager_can_override_with_existing_user(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_game_data,
    sample_guild,
    sample_user,
):
    """Test _resolve_game_host allows bot manager to override with existing user."""
    other_user = user_model.User(
        id=str(uuid.uuid4()),
        discord_id="999",
    )
    sample_game_data.host = "@otheruser"

    # Mock database calls: requester lookup, then resolved host lookup
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user

    resolved_host_result = MagicMock()
    resolved_host_result.scalar_one_or_none.return_value = other_user

    final_host_result = MagicMock()
    final_host_result.scalar_one_or_none.return_value = other_user

    mock_db.execute = AsyncMock(
        side_effect=[requester_result, resolved_host_result, final_host_result]
    )

    # Mock participant resolver
    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [{"type": "discord", "discord_id": "999"}],
            [],
        )
    )

    # Mock role service to allow bot manager
    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        host_user_id, host_user = await game_service._resolve_game_host(
            sample_game_data, sample_guild, sample_user.id, "token"
        )

    assert host_user_id == other_user.id
    assert host_user == other_user


@pytest.mark.asyncio
async def test_resolve_game_host_bot_manager_creates_new_user(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_game_data,
    sample_guild,
    sample_user,
):
    """Test _resolve_game_host creates new user when host doesn't exist in database."""
    sample_game_data.host = "@newuser"

    # Mock database calls
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user

    # Host doesn't exist initially
    resolved_host_result = MagicMock()
    resolved_host_result.scalar_one_or_none.return_value = None

    # After creation, host exists
    created_user = user_model.User(
        id=str(uuid.uuid4()),
        discord_id="888",
    )
    final_host_result = MagicMock()
    final_host_result.scalar_one_or_none.return_value = created_user

    mock_db.execute = AsyncMock(
        side_effect=[requester_result, resolved_host_result, final_host_result]
    )
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Mock participant resolver
    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [
                {
                    "type": "discord",
                    "discord_id": "888",
                }
            ],
            [],
        )
    )

    # Mock role service
    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        host_user_id, host_user = await game_service._resolve_game_host(
            sample_game_data, sample_guild, sample_user.id, "token"
        )

    assert host_user == created_user
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_game_host_invalid_mention_raises_validation_error(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_game_data,
    sample_guild,
    sample_user,
):
    """Test _resolve_game_host raises ValidationError for invalid mention."""
    sample_game_data.host = "@invaliduser"

    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute = AsyncMock(return_value=requester_result)

    # Mock participant resolver to return validation error
    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [],
            [{"input": "@invaliduser", "reason": "User not found", "suggestions": []}],
        )
    )

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(resolver_module.ValidationError):
            await game_service._resolve_game_host(
                sample_game_data, sample_guild, sample_user.id, "token"
            )


@pytest.mark.asyncio
async def test_resolve_game_host_placeholder_not_allowed(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_game_data,
    sample_guild,
    sample_user,
):
    """Test _resolve_game_host rejects placeholder (non-Discord) host."""
    sample_game_data.host = "PlaceholderName"

    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute = AsyncMock(return_value=requester_result)

    # Mock participant resolver to return placeholder type
    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [{"type": "placeholder", "display_name": "PlaceholderName"}],
            [],
        )
    )

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(resolver_module.ValidationError) as exc_info:
            await game_service._resolve_game_host(
                sample_game_data, sample_guild, sample_user.id, "token"
            )

        assert "must be a Discord user" in str(exc_info.value.invalid_mentions[0]["reason"])


@pytest.mark.asyncio
async def test_resolve_game_host_resolution_failure_wraps_exception(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_game_data,
    sample_guild,
    sample_user,
):
    """Test _resolve_game_host wraps non-ValidationError exceptions."""
    sample_game_data.host = "@someuser"

    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute = AsyncMock(return_value=requester_result)

    # Mock participant resolver to raise generic exception
    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        side_effect=Exception("Network error")
    )

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(ValueError, match="Failed to resolve host mention"):
            await game_service._resolve_game_host(
                sample_game_data, sample_guild, sample_user.id, "token"
            )


@pytest.mark.asyncio
async def test_create_participant_records_with_discord_user(
    game_service,
    mock_db,
    mock_participant_resolver,
):
    """Test _create_participant_records creates Discord user participant."""
    game_id = str(uuid.uuid4())
    discord_user = user_model.User(id=str(uuid.uuid4()), discord_id="123456")

    valid_participants = [{"type": "discord", "discord_id": "123456", "original_input": "@user1"}]

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=discord_user)
    mock_db.flush = AsyncMock()

    await game_service._create_participant_records(game_id, valid_participants)

    mock_participant_resolver.ensure_user_exists.assert_called_once_with(mock_db, "123456")
    mock_db.add.assert_called_once()
    added_participant = mock_db.add.call_args[0][0]
    assert isinstance(added_participant, participant_model.GameParticipant)
    assert added_participant.game_session_id == game_id
    assert added_participant.user_id == discord_user.id
    assert added_participant.display_name is None
    assert added_participant.position_type == ParticipantType.HOST_ADDED
    assert added_participant.position == 1
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_create_participant_records_with_placeholder(
    game_service,
    mock_db,
):
    """Test _create_participant_records creates placeholder participant."""
    game_id = str(uuid.uuid4())

    valid_participants = [
        {
            "type": "placeholder",
            "display_name": "John Doe",
            "original_input": "John Doe",
        }
    ]

    mock_db.flush = AsyncMock()

    await game_service._create_participant_records(game_id, valid_participants)

    mock_db.add.assert_called_once()
    added_participant = mock_db.add.call_args[0][0]
    assert isinstance(added_participant, participant_model.GameParticipant)
    assert added_participant.game_session_id == game_id
    assert added_participant.user_id is None
    assert added_participant.display_name == "John Doe"
    assert added_participant.position_type == ParticipantType.HOST_ADDED
    assert added_participant.position == 1
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_create_participant_records_with_mixed_participants(
    game_service,
    mock_db,
    mock_participant_resolver,
):
    """Test _create_participant_records handles mixed Discord and placeholder participants."""
    game_id = str(uuid.uuid4())
    discord_user1 = user_model.User(id=str(uuid.uuid4()), discord_id="111")
    discord_user2 = user_model.User(id=str(uuid.uuid4()), discord_id="222")

    valid_participants = [
        {"type": "discord", "discord_id": "111", "original_input": "@user1"},
        {"type": "placeholder", "display_name": "Alice", "original_input": "Alice"},
        {"type": "discord", "discord_id": "222", "original_input": "@user2"},
        {"type": "placeholder", "display_name": "Bob", "original_input": "Bob"},
    ]

    mock_participant_resolver.ensure_user_exists = AsyncMock(
        side_effect=[discord_user1, discord_user2]
    )
    mock_db.flush = AsyncMock()

    await game_service._create_participant_records(game_id, valid_participants)

    assert mock_participant_resolver.ensure_user_exists.call_count == 2
    assert mock_db.add.call_count == 4

    # Verify positions are sequential starting at 1
    added_participants = [call[0][0] for call in mock_db.add.call_args_list]
    assert added_participants[0].position == 1
    assert added_participants[0].user_id == discord_user1.id
    assert added_participants[1].position == 2
    assert added_participants[1].display_name == "Alice"
    assert added_participants[2].position == 3
    assert added_participants[2].user_id == discord_user2.id
    assert added_participants[3].position == 4
    assert added_participants[3].display_name == "Bob"
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_create_participant_records_empty_list(
    game_service,
    mock_db,
):
    """Test _create_participant_records handles empty participant list."""
    game_id = str(uuid.uuid4())
    valid_participants = []

    mock_db.flush = AsyncMock()

    await game_service._create_participant_records(game_id, valid_participants)

    mock_db.add.assert_not_called()
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_load_game_dependencies_success(
    game_service,
    mock_db,
    sample_guild,
    sample_template,
    sample_channel,
):
    """Test _load_game_dependencies successfully loads all dependencies."""
    mock_db.execute = AsyncMock(
        side_effect=[
            # Template query result
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_template)),
            # Guild query result
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_guild)),
            # Channel query result
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_channel)),
        ]
    )

    template, guild, channel = await game_service._load_game_dependencies(sample_template.id)

    assert template == sample_template
    assert guild == sample_guild
    assert channel == sample_channel
    assert mock_db.execute.call_count == 3


@pytest.mark.asyncio
async def test_load_game_dependencies_template_not_found(
    game_service,
    mock_db,
):
    """Test _load_game_dependencies raises ValueError when template not found."""
    template_id = str(uuid.uuid4())
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )

    with pytest.raises(ValueError, match=f"Template not found for ID: {template_id}"):
        await game_service._load_game_dependencies(template_id)


@pytest.mark.asyncio
async def test_load_game_dependencies_guild_not_found(
    game_service,
    mock_db,
    sample_template,
):
    """Test _load_game_dependencies raises ValueError when guild config not found."""
    mock_db.execute = AsyncMock(
        side_effect=[
            # Template query result
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_template)),
            # Guild query result - not found
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
    )

    with pytest.raises(
        ValueError,
        match=f"Guild configuration not found for ID: {sample_template.guild_id}",
    ):
        await game_service._load_game_dependencies(sample_template.id)


@pytest.mark.asyncio
async def test_load_game_dependencies_channel_not_found(
    game_service,
    mock_db,
    sample_guild,
    sample_template,
):
    """Test _load_game_dependencies raises ValueError when channel config not found."""
    mock_db.execute = AsyncMock(
        side_effect=[
            # Template query result
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_template)),
            # Guild query result
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_guild)),
            # Channel query result - not found
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
    )

    with pytest.raises(
        ValueError,
        match=f"Channel configuration not found for ID: {sample_template.channel_id}",
    ):
        await game_service._load_game_dependencies(sample_template.id)


@pytest.mark.asyncio
async def test_build_game_session_with_media_attachments(
    game_service,
    sample_template,
    sample_guild,
):
    """Test _build_game_session with media attachments stores images and returns FK IDs."""
    host_user = user_model.User(
        id=str(uuid.uuid4()),
        discord_id="123456",
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC),
    )

    resolved_fields = {
        "max_players": 5,
        "reminder_minutes": [60],
        "expected_duration_minutes": 120,
        "where": "Online",
        "signup_instructions": "Sign up here",
        "signup_method": SignupMethod.SELF_SIGNUP.value,
    }

    media = GameMediaAttachments(
        thumbnail_data=b"thumbnail",
        thumbnail_mime_type="image/png",
        image_data=b"image",
        image_mime_type="image/jpeg",
    )

    # Mock store_image to return UUIDs
    thumbnail_id = uuid.uuid4()
    banner_id = uuid.uuid4()
    with patch("services.api.services.games.store_image", new_callable=AsyncMock) as mock_store:
        mock_store.side_effect = [thumbnail_id, banner_id]

        game = await game_service._build_game_session(
            game_data, sample_template, sample_guild, host_user, resolved_fields, media
        )

    assert game.title == "Test Game"
    assert game.description == "Test description"
    assert game.template_id == sample_template.id
    assert game.guild_id == sample_guild.id
    assert game.channel_id == sample_template.channel_id
    assert game.host_id == host_user.id
    assert game.max_players == 5
    assert game.thumbnail_id == thumbnail_id
    assert game.banner_image_id == banner_id
    assert mock_store.call_count == 2


@pytest.mark.asyncio
async def test_build_game_session_without_media(
    game_service,
    sample_template,
    sample_guild,
):
    """Test _build_game_session without media attachments has None FK IDs."""
    host_user = user_model.User(
        id=str(uuid.uuid4()),
        discord_id="123456",
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC),
    )

    resolved_fields = {
        "max_players": 5,
        "reminder_minutes": [60],
        "expected_duration_minutes": 120,
        "where": "Online",
        "signup_instructions": "Sign up here",
        "signup_method": SignupMethod.SELF_SIGNUP.value,
    }

    media = GameMediaAttachments()

    game = await game_service._build_game_session(
        game_data, sample_template, sample_guild, host_user, resolved_fields, media
    )

    assert game.thumbnail_id is None
    assert game.banner_image_id is None


@pytest.mark.asyncio
async def test_build_game_session_timezone_normalization_aware(
    game_service,
    sample_template,
    sample_guild,
):
    """Test _build_game_session normalizes timezone-aware datetime to naive UTC."""
    host_user = user_model.User(
        id=str(uuid.uuid4()),
        discord_id="123456",
    )

    # Create a timezone-aware datetime
    scheduled_at_aware = datetime.datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)

    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=scheduled_at_aware,
    )

    resolved_fields = {
        "max_players": 5,
        "reminder_minutes": [60],
        "expected_duration_minutes": 120,
        "where": "Online",
        "signup_instructions": "Sign up here",
        "signup_method": SignupMethod.SELF_SIGNUP.value,
    }

    media = GameMediaAttachments()

    game = await game_service._build_game_session(
        game_data, sample_template, sample_guild, host_user, resolved_fields, media
    )

    # Should be naive UTC
    assert game.scheduled_at.tzinfo is None
    assert game.scheduled_at == datetime.datetime(2026, 6, 15, 12, 0, 0)


@pytest.mark.asyncio
async def test_build_game_session_timezone_normalization_naive(
    game_service,
    sample_template,
    sample_guild,
):
    """Test _build_game_session preserves naive datetime."""
    host_user = user_model.User(
        id=str(uuid.uuid4()),
        discord_id="123456",
    )

    # Create a naive datetime
    scheduled_at_naive = datetime.datetime(2026, 6, 15, 12, 0, 0)

    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=scheduled_at_naive,
    )

    resolved_fields = {
        "max_players": 5,
        "reminder_minutes": [60],
        "expected_duration_minutes": 120,
        "where": "Online",
        "signup_instructions": "Sign up here",
        "signup_method": SignupMethod.SELF_SIGNUP.value,
    }

    media = GameMediaAttachments()

    game = await game_service._build_game_session(
        game_data, sample_template, sample_guild, host_user, resolved_fields, media
    )

    # Should remain naive
    assert game.scheduled_at.tzinfo is None
    assert game.scheduled_at == scheduled_at_naive


@pytest.mark.asyncio
async def test_setup_game_schedules_with_reminders_and_duration(
    game_service,
    mock_db,
):
    """Test _setup_game_schedules calls all schedule methods with parameters."""
    scheduled_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        status=game_model.GameStatus.SCHEDULED.value,
    )

    reminder_minutes = [30, 60]
    expected_duration_minutes = 120

    with (
        patch.object(
            game_service,
            "_schedule_join_notifications_for_game",
            new_callable=AsyncMock,
        ) as mock_join_notifications,
        patch(
            "services.api.services.games.notification_schedule_service.NotificationScheduleService"
        ) as mock_schedule_service_class,
        patch.object(
            game_service, "_create_game_status_schedules", new_callable=AsyncMock
        ) as mock_status_schedules,
    ):
        mock_schedule_service = AsyncMock()
        mock_schedule_service.populate_schedule = AsyncMock()
        mock_schedule_service_class.return_value = mock_schedule_service

        await game_service._setup_game_schedules(game, reminder_minutes, expected_duration_minutes)

        mock_join_notifications.assert_called_once_with(game)
        mock_schedule_service.populate_schedule.assert_called_once_with(game, reminder_minutes)
        mock_status_schedules.assert_called_once_with(game, expected_duration_minutes)


@pytest.mark.asyncio
async def test_setup_game_schedules_without_reminders(
    game_service,
    mock_db,
):
    """Test _setup_game_schedules handles empty reminder list."""
    scheduled_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        status=game_model.GameStatus.SCHEDULED.value,
    )

    reminder_minutes: list[int] = []
    expected_duration_minutes = 120

    with (
        patch.object(
            game_service,
            "_schedule_join_notifications_for_game",
            new_callable=AsyncMock,
        ) as mock_join_notifications,
        patch(
            "services.api.services.games.notification_schedule_service.NotificationScheduleService"
        ) as mock_schedule_service_class,
        patch.object(
            game_service, "_create_game_status_schedules", new_callable=AsyncMock
        ) as mock_status_schedules,
    ):
        mock_schedule_service = AsyncMock()
        mock_schedule_service.populate_schedule = AsyncMock()
        mock_schedule_service_class.return_value = mock_schedule_service

        await game_service._setup_game_schedules(game, reminder_minutes, expected_duration_minutes)

        mock_join_notifications.assert_called_once_with(game)
        mock_schedule_service.populate_schedule.assert_called_once_with(game, reminder_minutes)
        mock_status_schedules.assert_called_once_with(game, expected_duration_minutes)


@pytest.mark.asyncio
async def test_setup_game_schedules_without_duration(
    game_service,
    mock_db,
):
    """Test _setup_game_schedules handles None duration."""
    scheduled_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        status=game_model.GameStatus.SCHEDULED.value,
    )

    reminder_minutes = [60]
    expected_duration_minutes = None

    with (
        patch.object(
            game_service,
            "_schedule_join_notifications_for_game",
            new_callable=AsyncMock,
        ) as mock_join_notifications,
        patch(
            "services.api.services.games.notification_schedule_service.NotificationScheduleService"
        ) as mock_schedule_service_class,
        patch.object(
            game_service, "_create_game_status_schedules", new_callable=AsyncMock
        ) as mock_status_schedules,
    ):
        mock_schedule_service = AsyncMock()
        mock_schedule_service.populate_schedule = AsyncMock()
        mock_schedule_service_class.return_value = mock_schedule_service

        await game_service._setup_game_schedules(game, reminder_minutes, expected_duration_minutes)

        mock_join_notifications.assert_called_once_with(game)
        mock_schedule_service.populate_schedule.assert_called_once_with(game, reminder_minutes)
        mock_status_schedules.assert_called_once_with(game, None)


@pytest.mark.asyncio
async def test_create_game_status_schedules_for_scheduled_game(
    game_service,
    mock_db,
):
    """Test _create_game_status_schedules creates both schedules for SCHEDULED game."""
    scheduled_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        status=game_model.GameStatus.SCHEDULED.value,
    )

    expected_duration = 90
    await game_service._create_game_status_schedules(game, expected_duration)

    assert mock_db.add.call_count == 2
    added_schedules = [call[0][0] for call in mock_db.add.call_args_list]

    # Verify IN_PROGRESS schedule
    in_progress_schedule = next(
        s for s in added_schedules if s.target_status == game_model.GameStatus.IN_PROGRESS.value
    )
    assert in_progress_schedule.game_id == game.id
    assert in_progress_schedule.transition_time == scheduled_time
    assert in_progress_schedule.executed is False

    # Verify COMPLETED schedule
    completed_schedule = next(
        s for s in added_schedules if s.target_status == game_model.GameStatus.COMPLETED.value
    )
    assert completed_schedule.game_id == game.id
    assert completed_schedule.transition_time == scheduled_time + datetime.timedelta(
        minutes=expected_duration
    )
    assert completed_schedule.executed is False


@pytest.mark.asyncio
async def test_create_game_status_schedules_uses_default_duration_when_none(
    game_service,
    mock_db,
):
    """Test _create_game_status_schedules uses default duration when None."""
    scheduled_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        status=game_model.GameStatus.SCHEDULED.value,
    )

    await game_service._create_game_status_schedules(game, None)

    assert mock_db.add.call_count == 2
    added_schedules = [call[0][0] for call in mock_db.add.call_args_list]

    # Verify COMPLETED schedule uses default duration
    completed_schedule = next(
        s for s in added_schedules if s.target_status == game_model.GameStatus.COMPLETED.value
    )
    expected_completion = scheduled_time + datetime.timedelta(minutes=DEFAULT_GAME_DURATION_MINUTES)
    assert completed_schedule.transition_time == expected_completion


@pytest.mark.asyncio
async def test_create_game_status_schedules_skips_non_scheduled_game(
    game_service,
    mock_db,
):
    """Test _create_game_status_schedules does not create schedules for non-SCHEDULED games."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        status=game_model.GameStatus.IN_PROGRESS.value,
    )

    await game_service._create_game_status_schedules(game, 90)

    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_game_status_schedules_with_custom_duration(
    game_service,
    mock_db,
):
    """Test _create_game_status_schedules uses custom duration when provided."""
    scheduled_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        status=game_model.GameStatus.SCHEDULED.value,
    )

    custom_duration = 180
    await game_service._create_game_status_schedules(game, custom_duration)

    added_schedules = [call[0][0] for call in mock_db.add.call_args_list]
    completed_schedule = next(
        s for s in added_schedules if s.target_status == game_model.GameStatus.COMPLETED.value
    )
    expected_completion = scheduled_time + datetime.timedelta(minutes=custom_duration)
    assert completed_schedule.transition_time == expected_completion


@pytest.mark.asyncio
async def test_create_game_without_participants(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_game_data,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test creating game without initial participants."""
    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
    )
    created_game.host = sample_user
    created_game.participants = []

    setup_create_game_mocks(
        mock_db,
        sample_template,
        sample_guild,
        sample_user,
        sample_channel,
        created_game,
    )
    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=sample_game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert isinstance(game, game_model.GameSession)
    assert game.title == "Test Game"
    assert game.host_id == sample_user.id
    mock_db.add.assert_called()
    mock_event_publisher.publish_deferred.assert_called_once()


@pytest.mark.asyncio
async def test_create_game_with_where_field(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test creating game with where field stores location."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        where="Discord Voice Channel #gaming",
        max_players=4,
        reminder_minutes=[60],
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        where="Discord Voice Channel #gaming",
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
    )
    created_game.host = sample_user
    created_game.participants = []

    setup_create_game_mocks(
        mock_db,
        sample_template,
        sample_guild,
        sample_user,
        sample_channel,
        created_game,
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert isinstance(game, game_model.GameSession)
    assert game.where == "Discord Voice Channel #gaming"
    mock_db.add.assert_called()


@pytest.mark.asyncio
async def test_create_game_with_valid_participants(
    game_service,
    mock_db,
    mock_participant_resolver,
    mock_role_service,
    sample_game_data,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test creating game resolves and delegates participant creation."""
    sample_game_data.initial_participants = ["@user1", "Placeholder"]

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
    )
    created_game.host = sample_user
    created_game.participants = []

    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [
                {"type": "discord", "discord_id": "444", "original_input": "@user1"},
                {
                    "type": "placeholder",
                    "display_name": "Placeholder",
                    "original_input": "Placeholder",
                },
            ],
            [],
        )
    )
    mock_participant_resolver.ensure_user_exists = AsyncMock(
        return_value=user_model.User(id=str(uuid.uuid4()), discord_id="444")
    )

    setup_create_game_mocks(
        mock_db,
        sample_template,
        sample_guild,
        sample_user,
        sample_channel,
        created_game,
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=sample_game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert isinstance(game, game_model.GameSession)
    mock_participant_resolver.resolve_initial_participants.assert_called_once()


@pytest.mark.asyncio
async def test_create_game_with_invalid_participants(
    game_service,
    mock_db,
    mock_participant_resolver,
    mock_role_service,
    sample_game_data,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test creating game with invalid @mentions raises ValidationError."""
    sample_game_data.initial_participants = ["@invalid"]

    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [],
            [{"input": "@invalid", "reason": "User not found", "suggestions": []}],
        )
    )

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    mock_db.execute = AsyncMock(
        side_effect=[template_result, guild_result, channel_result, host_result]
    )
    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    with (
        patch("services.api.auth.roles.get_role_service", return_value=mock_role_service),
        pytest.raises(resolver_module.ValidationError) as exc_info,
    ):
        await game_service.create_game(
            game_data=sample_game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert len(exc_info.value.invalid_mentions) == 1
    assert exc_info.value.invalid_mentions[0]["input"] == "@invalid"


@pytest.mark.asyncio
async def test_create_game_timezone_conversion(
    game_service,
    mock_db,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that timezone-aware datetimes are properly converted to UTC."""
    # Create game with EST time (UTC-5)
    est = datetime.timezone(datetime.timedelta(hours=-5))
    # 10 AM EST = 3 PM UTC (15:00)
    scheduled_time_est = datetime.datetime(2025, 11, 20, 10, 0, 0, tzinfo=est)

    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Timezone Test",
        description="Test timezone conversion",
        scheduled_at=scheduled_time_est,
        max_players=4,
        reminder_minutes=[60],
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Timezone Test",
        description="Test timezone conversion",
        scheduled_at=datetime.datetime(2025, 11, 20, 15, 0, 0).replace(tzinfo=None),  # Naive UTC
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
    )
    created_game.host = sample_user
    created_game.participants = []

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = created_game
    get_game_result = MagicMock()
    get_game_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            host_result,
            reload_result,
            get_game_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    # Capture the game object when it's added to verify timezone conversion
    added_game = None

    def capture_add(obj):
        nonlocal added_game
        if isinstance(obj, game_model.GameSession):
            added_game = obj
            obj.id = created_game.id
            obj.channel_id = created_game.channel_id

    mock_db.add = MagicMock(side_effect=capture_add)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    # Verify the stored time was converted to UTC (15:00, not 10:00)
    assert added_game is not None
    assert added_game.scheduled_at.hour == 15  # 3 PM UTC
    assert added_game.scheduled_at.minute == 0
    assert added_game.scheduled_at.tzinfo is None  # Should be naive (UTC implied)


@pytest.mark.asyncio
async def test_get_game_found(game_service, mock_db):
    """Test getting game by ID returns game."""
    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(id=game_id, title="Test")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    game = await game_service.get_game(game_id)

    assert game is mock_game


@pytest.mark.asyncio
async def test_get_game_not_found(game_service, mock_db):
    """Test getting non-existent game returns None."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    game = await game_service.get_game(str(uuid.uuid4()))

    assert game is None


@pytest.mark.asyncio
async def test_list_games_no_filters(game_service, mock_db):
    """Test listing games without filters."""
    mock_games = [
        game_model.GameSession(id=str(uuid.uuid4()), title="Game 1"),
        game_model.GameSession(id=str(uuid.uuid4()), title="Game 2"),
    ]

    count_result = MagicMock()
    count_result.scalar.return_value = 2
    games_result = MagicMock()
    games_result.scalars.return_value.all.return_value = mock_games

    mock_db.execute = AsyncMock(side_effect=[count_result, games_result])

    games, count = await game_service.list_games()

    assert len(games) == 2
    assert count == 2


@pytest.mark.asyncio
async def test_list_games_with_filters(game_service, mock_db, sample_guild):
    """Test listing games with guild and status filters."""
    mock_games = [game_model.GameSession(id=str(uuid.uuid4()), title="Filtered")]

    count_result = MagicMock()
    count_result.scalar.return_value = 1
    games_result = MagicMock()
    games_result.scalars.return_value.all.return_value = mock_games

    mock_db.execute = AsyncMock(side_effect=[count_result, games_result])

    games, count = await game_service.list_games(guild_id=str(sample_guild.id), status="SCHEDULED")

    assert len(games) == 1
    assert count == 1


@pytest.mark.asyncio
async def test_update_game_success(game_service, mock_db, sample_user, sample_guild):
    """Test updating game by host."""

    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=sample_guild.id,
    )
    mock_game = game_model.GameSession(
        id=game_id,
        title="Old Title",
        host_id=sample_user.id,
        guild_id=sample_guild.id,
        channel_id=channel_id,
        scheduled_at=datetime.datetime.now(UTC).replace(tzinfo=None),
        status="SCHEDULED",
    )
    mock_game.host = sample_user
    mock_game.guild = sample_guild
    mock_game.channel = mock_channel
    mock_game.participants = []

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)
    mock_db.commit = AsyncMock()

    # Mock current user
    current_user = CurrentUser(
        user=sample_user, access_token="mock_token", session_token="mock_session"
    )

    # Mock role service with can_manage_game patched
    mock_role_service = MagicMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        updated = await game_service.update_game(
            game_id=game_id,
            update_data=game_schemas.GameUpdateRequest(
                title="New Title",
                description="Updated description",
                status="SCHEDULED",
            ),
            current_user=current_user,
            role_service=mock_role_service,
        )

    assert updated.title == "New Title"


@pytest.mark.asyncio
async def test_update_game_where_field(game_service, mock_db, sample_user, sample_guild):
    """Test updating game where field."""

    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=sample_guild.id,
    )
    mock_game = game_model.GameSession(
        id=game_id,
        title="Test Game",
        where="Old Location",
        host_id=sample_user.id,
        guild_id=sample_guild.id,
        channel_id=channel_id,
    )
    mock_game.host = sample_user
    mock_game.guild = sample_guild
    mock_game.channel = mock_channel

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)
    mock_db.commit = AsyncMock()

    current_user = CurrentUser(
        user=sample_user, access_token="mock_token", session_token="mock_session"
    )
    mock_role_service = MagicMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        updated = await game_service.update_game(
            game_id=game_id,
            update_data=game_schemas.GameUpdateRequest(where="New Location"),
            current_user=current_user,
            role_service=mock_role_service,
        )

    assert updated.where == "New Location"


@pytest.mark.asyncio
async def test_update_game_not_host(game_service, mock_db, sample_user, sample_guild):
    """Test updating game by non-host raises ValueError."""

    game_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())
    other_user = user_model.User(id=other_user_id, discord_id="otheruser123")
    mock_game = game_model.GameSession(
        id=game_id,
        title="Title",
        host_id=other_user_id,
        guild_id=sample_guild.id,
        channel_id=str(uuid.uuid4()),
    )
    mock_game.host = other_user
    mock_game.guild = sample_guild

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)

    # Mock current user (not the host)
    current_user = CurrentUser(
        user=sample_user, access_token="mock_token", session_token="mock_session"
    )

    mock_role_service = MagicMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=False):
        with pytest.raises(ValueError, match="You don't have permission to update"):
            await game_service.update_game(
                game_id=game_id,
                update_data=game_schemas.GameUpdateRequest(
                    title="New Title",
                    description="Updated description",
                    status="SCHEDULED",
                ),
                current_user=current_user,
                role_service=mock_role_service,
            )


@pytest.mark.asyncio
async def test_delete_game_success(game_service, mock_db, sample_user, sample_guild):
    """Test deleting game by host."""

    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=sample_guild.id,
    )
    mock_game = game_model.GameSession(
        id=game_id,
        title="Title",
        host_id=sample_user.id,
        status="SCHEDULED",
        guild_id=sample_guild.id,
        channel_id=channel_id,
    )
    mock_game.host = sample_user
    mock_game.guild = sample_guild
    mock_game.channel = mock_channel

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)
    mock_db.commit = AsyncMock()

    # Mock current user
    current_user = CurrentUser(
        user=sample_user, access_token="mock_token", session_token="mock_session"
    )

    mock_role_service = MagicMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        await game_service.delete_game(
            game_id=game_id,
            current_user=current_user,
            role_service=mock_role_service,
        )

    assert mock_game.status == "CANCELLED"


@pytest.mark.asyncio
async def test_join_game_success(
    game_service, mock_db, mock_participant_resolver, sample_guild, sample_channel
):
    """Test successfully joining a game."""
    game_id = str(uuid.uuid4())
    new_user = user_model.User(id=str(uuid.uuid4()), discord_id="999")
    mock_game = game_model.GameSession(
        id=game_id,
        status="SCHEDULED",
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        max_players=5,
    )
    mock_game.channel = sample_channel
    mock_game.participants = []

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game

    # Mock existing participant check (None = user not already in game)
    existing_participant_result = MagicMock()
    existing_participant_result.scalar_one_or_none.return_value = None

    # Mock the participant count query
    count_result = MagicMock()
    count_result.scalar.return_value = 0

    # Mock guild/channel queries for max_players resolution
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel

    # Mock the second count query in _publish_game_updated
    count_result2 = MagicMock()
    count_result2.scalar.return_value = 1

    mock_db.execute = AsyncMock(
        side_effect=[
            game_result,
            existing_participant_result,
            count_result,
            guild_result,
            channel_result,
            count_result2,
        ]
    )
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=new_user)

    await game_service.join_game(game_id=game_id, user_discord_id=new_user.discord_id)

    mock_db.add.assert_called()
    # Flush is called twice: once for participant ID, once in schedule_join_notification
    assert mock_db.flush.call_count == 2


@pytest.mark.asyncio
async def test_join_game_already_joined(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_user,
    sample_guild,
    sample_channel,
):
    """Test joining same game twice is idempotent (returns existing participant)."""

    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(
        id=game_id,
        status="SCHEDULED",
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        max_players=5,
    )
    mock_participant = participant_model.GameParticipant(
        user_id=sample_user.id,
        game_session_id=game_id,
        position_type=ParticipantType.SELF_ADDED,
        position=0,
    )
    mock_game.participants = [mock_participant]

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game

    # Mock existing participant check (returns existing participant)
    existing_participant_result = MagicMock()
    existing_participant_result.scalar_one_or_none.return_value = mock_participant

    mock_db.execute = AsyncMock(side_effect=[game_result, existing_participant_result])

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    # Should return existing participant without error (idempotent)
    result = await game_service.join_game(game_id=game_id, user_discord_id=sample_user.discord_id)

    assert result == mock_participant


@pytest.mark.asyncio
async def test_join_game_full(
    game_service, mock_db, mock_participant_resolver, sample_guild, sample_channel
):
    """Test joining full game raises ValueError."""
    game_id = str(uuid.uuid4())
    new_user = user_model.User(id=str(uuid.uuid4()), discord_id="999")
    mock_game = game_model.GameSession(id=game_id, status="SCHEDULED", max_players=2)
    mock_game.participants = []
    mock_game.guild_id = sample_guild.id
    mock_game.channel_id = sample_channel.id

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game

    # Mock existing participant check (None = user not already in game)
    existing_participant_result = MagicMock()
    existing_participant_result.scalar_one_or_none.return_value = None

    # Mock the participant count query (2 non-placeholder participants)
    count_result = MagicMock()
    count_result.scalar.return_value = 2

    # Mock guild and channel config for max_players resolution
    guild_result = MagicMock()
    guild_result.scalar_one.return_value = sample_guild

    channel_result = MagicMock()
    channel_result.scalar_one.return_value = sample_channel

    mock_db.execute = AsyncMock(
        side_effect=[
            game_result,
            existing_participant_result,
            count_result,
            guild_result,
            channel_result,
        ]
    )

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=new_user)

    with pytest.raises(ValueError, match="Game is full"):
        await game_service.join_game(game_id=game_id, user_discord_id=new_user.discord_id)


@pytest.mark.asyncio
async def test_leave_game_success(game_service, mock_db, sample_user):
    """Test user leaving game successfully."""
    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=str(uuid.uuid4()),
    )
    mock_game = game_model.GameSession(
        id=game_id, title="Title", guild_id=uuid.uuid4(), channel_id=channel_id
    )
    mock_game.channel = mock_channel
    mock_participant = participant_model.GameParticipant(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        position_type=ParticipantType.SELF_ADDED,
        position=0,
    )
    mock_game.participants = [mock_participant]

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = sample_user
    participant_result = MagicMock()
    participant_result.scalar_one_or_none.return_value = mock_participant
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = None
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(
        side_effect=[
            game_result,
            user_result,
            participant_result,
            count_result,
            guild_result,
            channel_result,
        ]
    )
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    await game_service.leave_game(game_id=game_id, user_discord_id=sample_user.discord_id)

    mock_db.delete.assert_called_once_with(mock_participant)


@pytest.mark.asyncio
async def test_leave_game_not_participant(game_service, mock_db, sample_user):
    """Test non-participant leaving game is idempotent (no error)."""
    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(id=game_id, title="Title")
    mock_game.participants = []

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = sample_user
    participant_result = MagicMock()
    participant_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(side_effect=[game_result, user_result, participant_result])
    mock_db.delete = AsyncMock()

    # Should return without error (idempotent)
    await game_service.leave_game(game_id=game_id, user_discord_id=sample_user.discord_id)

    # Verify no delete was called since user wasn't in game
    mock_db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_in_progress_schedule_creates_new(game_service, mock_db, sample_game_data):
    """Test _ensure_in_progress_schedule creates new schedule when none exists."""

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        expected_duration_minutes=120,
        status="SCHEDULED",
    )
    existing_schedules: list[game_status_schedule_model.GameStatusSchedule] = []

    mock_db.add = MagicMock()

    await game_service._ensure_in_progress_schedule(game, existing_schedules)

    mock_db.add.assert_called_once()
    added_schedule = mock_db.add.call_args[0][0]
    assert isinstance(added_schedule, game_status_schedule_model.GameStatusSchedule)
    assert added_schedule.game_id == game.id
    assert added_schedule.target_status == game_model.GameStatus.IN_PROGRESS.value
    assert added_schedule.transition_time == game.scheduled_at
    assert added_schedule.executed is False


@pytest.mark.asyncio
async def test_ensure_in_progress_schedule_updates_existing(game_service, mock_db):
    """Test _ensure_in_progress_schedule updates existing schedule."""

    old_time = datetime.datetime.now(datetime.UTC)
    new_time = old_time + datetime.timedelta(hours=1)

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=new_time,
        expected_duration_minutes=120,
        status="SCHEDULED",
    )

    existing_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.IN_PROGRESS.value,
        transition_time=old_time,
        executed=True,
    )
    existing_schedules = [existing_schedule]

    mock_db.add = MagicMock()

    await game_service._ensure_in_progress_schedule(game, existing_schedules)

    mock_db.add.assert_not_called()
    assert existing_schedule.transition_time == new_time
    assert existing_schedule.executed is False


@pytest.mark.asyncio
async def test_ensure_completed_schedule_creates_new(game_service, mock_db):
    """Test _ensure_completed_schedule creates new schedule when none exists."""

    scheduled_time = datetime.datetime.now(datetime.UTC)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        expected_duration_minutes=60,
        status="SCHEDULED",
    )
    existing_schedules: list[game_status_schedule_model.GameStatusSchedule] = []

    mock_db.add = MagicMock()

    await game_service._ensure_completed_schedule(game, existing_schedules)

    mock_db.add.assert_called_once()
    added_schedule = mock_db.add.call_args[0][0]
    assert isinstance(added_schedule, game_status_schedule_model.GameStatusSchedule)
    assert added_schedule.game_id == game.id
    assert added_schedule.target_status == game_model.GameStatus.COMPLETED.value
    expected_time = scheduled_time + datetime.timedelta(minutes=60)
    assert added_schedule.transition_time == expected_time
    assert added_schedule.executed is False


@pytest.mark.asyncio
async def test_ensure_completed_schedule_uses_default_duration(game_service, mock_db):
    """Test _ensure_completed_schedule uses DEFAULT_GAME_DURATION_MINUTES when duration is None."""

    scheduled_time = datetime.datetime.now(datetime.UTC)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        expected_duration_minutes=None,
        status="SCHEDULED",
    )
    existing_schedules: list[game_status_schedule_model.GameStatusSchedule] = []

    mock_db.add = MagicMock()

    await game_service._ensure_completed_schedule(game, existing_schedules)

    mock_db.add.assert_called_once()
    added_schedule = mock_db.add.call_args[0][0]
    # Should use DEFAULT_GAME_DURATION_MINUTES (60)
    expected_time = scheduled_time + datetime.timedelta(minutes=60)
    assert added_schedule.transition_time == expected_time


@pytest.mark.asyncio
async def test_ensure_completed_schedule_updates_existing(game_service, mock_db):
    """Test _ensure_completed_schedule updates existing schedule."""

    old_time = datetime.datetime.now(datetime.UTC)
    new_scheduled_time = old_time + datetime.timedelta(hours=2)

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=new_scheduled_time,
        expected_duration_minutes=90,
        status="SCHEDULED",
    )

    existing_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.COMPLETED.value,
        transition_time=old_time,
        executed=True,
    )
    existing_schedules = [existing_schedule]

    mock_db.add = MagicMock()

    await game_service._ensure_completed_schedule(game, existing_schedules)

    mock_db.add.assert_not_called()
    expected_time = new_scheduled_time + datetime.timedelta(minutes=90)
    assert existing_schedule.transition_time == expected_time
    assert existing_schedule.executed is False


@pytest.mark.asyncio
async def test_update_status_schedules_for_scheduled_game(game_service, mock_db):
    """Test _update_status_schedules ensures both schedules exist for SCHEDULED game."""

    scheduled_time = datetime.datetime.now(datetime.UTC)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        expected_duration_minutes=60,
        status="SCHEDULED",
    )

    schedules_result = MagicMock()
    schedules_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=schedules_result)
    mock_db.add = MagicMock()

    await game_service._update_status_schedules(game)

    # Should add both IN_PROGRESS and COMPLETED schedules
    assert mock_db.add.call_count == 2
    added_schedules = [call[0][0] for call in mock_db.add.call_args_list]

    in_progress_schedule = next(
        s for s in added_schedules if s.target_status == game_model.GameStatus.IN_PROGRESS.value
    )
    completed_schedule = next(
        s for s in added_schedules if s.target_status == game_model.GameStatus.COMPLETED.value
    )

    assert in_progress_schedule.transition_time == scheduled_time
    assert completed_schedule.transition_time == scheduled_time + datetime.timedelta(minutes=60)


@pytest.mark.asyncio
async def test_update_status_schedules_deletes_for_non_scheduled_game(game_service, mock_db):
    """Test _update_status_schedules deletes all schedules for non-SCHEDULED game."""

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        expected_duration_minutes=60,
        status="IN_PROGRESS",
    )

    schedule1 = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.IN_PROGRESS.value,
        transition_time=datetime.datetime.now(datetime.UTC),
        executed=False,
    )
    schedule2 = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.COMPLETED.value,
        transition_time=datetime.datetime.now(datetime.UTC),
        executed=False,
    )

    schedules_result = MagicMock()
    schedules_result.scalars.return_value.all.return_value = [schedule1, schedule2]
    mock_db.execute = AsyncMock(return_value=schedules_result)
    mock_db.delete = AsyncMock()

    await game_service._update_status_schedules(game)

    # Should delete both schedules
    assert mock_db.delete.call_count == 2
    deleted_schedules = [call[0][0] for call in mock_db.delete.call_args_list]
    assert schedule1 in deleted_schedules
    assert schedule2 in deleted_schedules


@pytest.mark.asyncio
async def test_update_status_schedules_updates_existing_schedules(game_service, mock_db):
    """Test _update_status_schedules updates existing schedules for SCHEDULED game."""

    old_time = datetime.datetime.now(datetime.UTC)
    new_time = old_time + datetime.timedelta(days=1)

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=new_time,
        expected_duration_minutes=120,
        status="SCHEDULED",
    )

    in_progress_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.IN_PROGRESS.value,
        transition_time=old_time,
        executed=True,
    )
    completed_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.COMPLETED.value,
        transition_time=old_time + datetime.timedelta(minutes=60),
        executed=True,
    )

    schedules_result = MagicMock()
    schedules_result.scalars.return_value.all.return_value = [
        in_progress_schedule,
        completed_schedule,
    ]
    mock_db.execute = AsyncMock(return_value=schedules_result)
    mock_db.add = MagicMock()

    await game_service._update_status_schedules(game)

    # Should not add new schedules
    mock_db.add.assert_not_called()

    # Should update existing schedules
    assert in_progress_schedule.transition_time == new_time
    assert in_progress_schedule.executed is False
    assert completed_schedule.transition_time == new_time + datetime.timedelta(minutes=120)
    assert completed_schedule.executed is False


@pytest.mark.asyncio
async def test_create_game_creates_status_schedules(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test create_game creates both IN_PROGRESS and COMPLETED status schedules."""

    scheduled_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=scheduled_time,
        max_players=4,
        expected_duration_minutes=90,
        reminder_minutes=[60],
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        description="Test description",
        scheduled_at=scheduled_time,
        expected_duration_minutes=90,
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
    )
    created_game.host = sample_user
    created_game.participants = []

    # Track objects added to the database
    added_objects = []

    def track_add(obj):
        added_objects.append(obj)
        if isinstance(obj, game_model.GameSession):
            obj.id = created_game.id
            obj.channel_id = created_game.channel_id

    setup_create_game_mocks(
        mock_db,
        sample_template,
        sample_guild,
        sample_user,
        sample_channel,
        created_game,
    )
    mock_db.add.side_effect = track_add

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="mock_token",
        )

    # Verify status schedules were created
    status_schedules = [
        obj
        for obj in added_objects
        if isinstance(obj, game_status_schedule_model.GameStatusSchedule)
    ]
    assert len(status_schedules) == 2

    in_progress_schedule = next(
        s for s in status_schedules if s.target_status == game_model.GameStatus.IN_PROGRESS.value
    )
    completed_schedule = next(
        s for s in status_schedules if s.target_status == game_model.GameStatus.COMPLETED.value
    )

    assert in_progress_schedule.game_id == created_game.id
    # Compare times without timezone (SQLAlchemy may strip timezone)
    assert in_progress_schedule.transition_time.replace(tzinfo=None) == scheduled_time.replace(
        tzinfo=None
    )
    assert in_progress_schedule.executed is False

    assert completed_schedule.game_id == created_game.id
    expected_completion = scheduled_time + datetime.timedelta(minutes=90)
    assert completed_schedule.transition_time.replace(tzinfo=None) == expected_completion.replace(
        tzinfo=None
    )
    assert completed_schedule.executed is False


# Host Override Tests


@pytest.mark.asyncio
async def test_create_game_with_empty_host_defaults_to_current_user(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that empty host field defaults to current user (backward compatibility)."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        host=None,
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
    )
    created_game.host = sample_user
    created_game.participants = []

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user
    reload_result = MagicMock()
    reload_result.scalar_one.return_value = created_game
    get_game_result = MagicMock()
    get_game_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            host_result,
            reload_result,
            get_game_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert game.host_id == sample_user.id


@pytest.mark.asyncio
async def test_create_game_regular_user_cannot_override_host(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that regular user cannot specify different host."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        host="@different_user",
    )

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            requester_result,
        ]
    )

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=False)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(ValueError, match="Only bot managers can specify the game host"):
            await game_service.create_game(
                game_data=game_data,
                host_user_id=sample_user.id,
                access_token="token",
            )


@pytest.mark.asyncio
async def test_create_game_bot_manager_can_override_host(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that bot manager can specify different user as host."""
    different_host = user_model.User(id=str(uuid.uuid4()), discord_id="999888777")

    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        host="@different_host",
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=different_host.id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
    )
    created_game.host = different_host
    created_game.participants = []

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user
    resolved_host_result = MagicMock()
    resolved_host_result.scalar_one_or_none.return_value = different_host
    final_host_result = MagicMock()
    final_host_result.scalar_one_or_none.return_value = different_host
    reload_result = MagicMock()
    reload_result.scalar_one.return_value = created_game
    get_game_result = MagicMock()
    get_game_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            requester_result,
            resolved_host_result,
            final_host_result,
            reload_result,
            get_game_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)
    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [
                {
                    "type": "discord",
                    "discord_id": different_host.discord_id,
                    "username": "different_host",
                    "display_name": "Different Host",
                    "original_input": "@different_host",
                }
            ],
            [],
        )
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert game.host_id == different_host.id


@pytest.mark.asyncio
async def test_create_game_bot_manager_invalid_host_raises_validation_error(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that invalid host mention raises validation error."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        host="@invalid_user",
    )

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            requester_result,
        ]
    )

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [],
            [
                {
                    "mention": "@invalid_user",
                    "error": "User not found",
                    "suggestions": [],
                }
            ],
        )
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(resolver_module.ValidationError) as exc_info:
            await game_service.create_game(
                game_data=game_data,
                host_user_id=sample_user.id,
                access_token="token",
            )

        assert len(exc_info.value.invalid_mentions) == 1
        assert exc_info.value.invalid_mentions[0]["mention"] == "@invalid_user"


@pytest.mark.asyncio
async def test_create_game_bot_manager_host_without_permissions_fails(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that host without required role permissions fails."""
    template_with_restrictions = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        name="Restricted Template",
        order=0,
        is_default=False,
        allowed_host_role_ids=["role123", "role456"],
        max_players=10,
        reminder_minutes=[60, 15],
    )

    different_host = user_model.User(id=str(uuid.uuid4()), discord_id="999888777")

    game_data = game_schemas.GameCreateRequest(
        template_id=template_with_restrictions.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        host="@different_host",
    )

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = template_with_restrictions
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user
    resolved_host_result = MagicMock()
    resolved_host_result.scalar_one_or_none.return_value = different_host
    final_host_result = MagicMock()
    final_host_result.scalar_one_or_none.return_value = different_host

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            requester_result,
            resolved_host_result,
            final_host_result,
        ]
    )
    mock_db.flush = AsyncMock()

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)
    mock_role_service.check_game_host_permission = AsyncMock(return_value=False)

    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [
                {
                    "type": "discord",
                    "discord_id": different_host.discord_id,
                    "username": "different_host",
                    "display_name": "Different Host",
                    "original_input": "@different_host",
                }
            ],
            [],
        )
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(
            ValueError,
            match="User does not have permission to create games with this template",
        ):
            await game_service.create_game(
                game_data=game_data,
                host_user_id=sample_user.id,
                access_token="token",
            )


@pytest.mark.asyncio
async def test_create_game_bot_manager_empty_host_uses_self(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that bot manager with empty host field defaults to themselves."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        host="",
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
    )
    created_game.host = sample_user
    created_game.participants = []

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user
    reload_result = MagicMock()
    reload_result.scalar_one.return_value = created_game
    get_game_result = MagicMock()
    get_game_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            host_result,
            reload_result,
            get_game_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert game.host_id == sample_user.id


@pytest.mark.asyncio
async def test_create_game_validates_signup_method_against_allowed_list(
    game_service,
    mock_db,
    mock_role_service,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test creating game validates signup method against template's allowed list."""

    template_with_restrictions = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        name="Restricted Template",
        order=0,
        is_default=True,
        max_players=10,
        reminder_minutes=[60, 15],
        allowed_signup_methods=[SignupMethod.HOST_SELECTED.value],
        default_signup_method=SignupMethod.HOST_SELECTED.value,
    )

    game_data = game_schemas.GameCreateRequest(
        template_id=template_with_restrictions.id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        signup_method=SignupMethod.SELF_SIGNUP.value,
    )

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = template_with_restrictions
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    mock_db.execute = AsyncMock(
        side_effect=[template_result, guild_result, channel_result, host_result]
    )
    mock_role_service.check_game_host_permission = AsyncMock(return_value=True)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(ValueError, match="not allowed for this template"):
            await game_service.create_game(
                game_data=game_data,
                host_user_id=sample_user.id,
                access_token="token",
            )


# Tests for _separate_existing_and_new_participants


def test_separate_existing_and_new_participants_with_existing_only(game_service):
    """Test separation with only existing participant IDs."""
    participant_data = [
        {"participant_id": "id-1", "position": 1},
        {"participant_id": "id-2", "position": 2},
        {"participant_id": "id-3", "position": 3},
    ]

    existing_ids, mentions = game_service._separate_existing_and_new_participants(participant_data)

    assert existing_ids == {"id-1", "id-2", "id-3"}
    assert mentions == []


def test_separate_existing_and_new_participants_with_mentions_only(game_service):
    """Test separation with only new mentions."""
    participant_data = [
        {"mention": "@user1", "position": 1},
        {"mention": "@user2", "position": 2},
        {"mention": "placeholder", "position": 3},
    ]

    existing_ids, mentions = game_service._separate_existing_and_new_participants(participant_data)

    assert existing_ids == set()
    assert mentions == [("@user1", 1), ("@user2", 2), ("placeholder", 3)]


def test_separate_existing_and_new_participants_mixed(game_service):
    """Test separation with both existing IDs and new mentions."""
    participant_data = [
        {"participant_id": "id-1", "position": 1},
        {"mention": "@user1", "position": 2},
        {"participant_id": "id-2", "position": 3},
        {"mention": "placeholder", "position": 4},
    ]

    existing_ids, mentions = game_service._separate_existing_and_new_participants(participant_data)

    assert existing_ids == {"id-1", "id-2"}
    assert mentions == [("@user1", 2), ("placeholder", 4)]


def test_separate_existing_and_new_participants_ignores_empty_mentions(game_service):
    """Test that empty or whitespace-only mentions are ignored."""
    participant_data = [
        {"participant_id": "id-1", "position": 1},
        {"mention": "", "position": 2},
        {"mention": "   ", "position": 3},
        {"mention": "@user1", "position": 4},
    ]

    existing_ids, mentions = game_service._separate_existing_and_new_participants(participant_data)

    assert existing_ids == {"id-1"}
    assert mentions == [("@user1", 4)]


def test_separate_existing_and_new_participants_uses_default_position(game_service):
    """Test that position defaults to 0 when not provided."""
    participant_data = [
        {"mention": "@user1"},
        {"mention": "@user2", "position": 5},
    ]

    existing_ids, mentions = game_service._separate_existing_and_new_participants(participant_data)

    assert existing_ids == set()
    assert mentions == [("@user1", 0), ("@user2", 5)]


# Tests for _remove_outdated_participants


@pytest.mark.asyncio
async def test_remove_outdated_participants_removes_missing_ids(game_service):
    """Test that participants not in existing_ids are deleted."""
    participant1 = MagicMock(id="id-1")
    participant2 = MagicMock(id="id-2")
    participant3 = MagicMock(id="id-3")
    current_participants = [participant1, participant2, participant3]

    existing_ids = {"id-1", "id-3"}

    await game_service._remove_outdated_participants(current_participants, existing_ids)

    game_service.db.delete.assert_called_once_with(participant2)


@pytest.mark.asyncio
async def test_remove_outdated_participants_keeps_all_when_all_present(game_service):
    """Test that no participants are deleted when all IDs are in existing_ids."""
    participant1 = MagicMock(id="id-1")
    participant2 = MagicMock(id="id-2")
    current_participants = [participant1, participant2]

    existing_ids = {"id-1", "id-2"}

    await game_service._remove_outdated_participants(current_participants, existing_ids)

    game_service.db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_remove_outdated_participants_removes_multiple(game_service):
    """Test that multiple outdated participants are deleted."""
    participant1 = MagicMock(id="id-1")
    participant2 = MagicMock(id="id-2")
    participant3 = MagicMock(id="id-3")
    participant4 = MagicMock(id="id-4")
    current_participants = [participant1, participant2, participant3, participant4]

    existing_ids = {"id-2"}

    await game_service._remove_outdated_participants(current_participants, existing_ids)

    assert game_service.db.delete.call_count == 3
    game_service.db.delete.assert_any_call(participant1)
    game_service.db.delete.assert_any_call(participant3)
    game_service.db.delete.assert_any_call(participant4)


@pytest.mark.asyncio
async def test_remove_outdated_participants_empty_list(game_service):
    """Test that no deletions occur with empty participant list."""
    current_participants = []
    existing_ids = {"id-1"}

    await game_service._remove_outdated_participants(current_participants, existing_ids)

    game_service.db.delete.assert_not_called()


# Tests for _update_participant_positions


def test_update_participant_positions_updates_matching_ids(game_service):
    """Test that positions are updated for matching participant IDs."""
    participant1 = MagicMock(id="id-1", position=0)
    participant2 = MagicMock(id="id-2", position=0)
    participant3 = MagicMock(id="id-3", position=0)
    current_participants = [participant1, participant2, participant3]

    participant_data = [
        {"participant_id": "id-1", "position": 10},
        {"participant_id": "id-2", "position": 20},
        {"participant_id": "id-3", "position": 30},
    ]

    game_service._update_participant_positions(current_participants, participant_data)

    assert participant1.position == 10
    assert participant2.position == 20
    assert participant3.position == 30


def test_update_participant_positions_ignores_non_matching_ids(game_service):
    """Test that positions are not changed for non-matching IDs."""
    participant1 = MagicMock(id="id-1", position=5)
    participant2 = MagicMock(id="id-2", position=10)
    current_participants = [participant1, participant2]

    participant_data = [
        {"participant_id": "id-99", "position": 100},
    ]

    game_service._update_participant_positions(current_participants, participant_data)

    assert participant1.position == 5
    assert participant2.position == 10


def test_update_participant_positions_ignores_mentions(game_service):
    """Test that mention-only data (no participant_id) is ignored."""
    participant1 = MagicMock(id="id-1", position=5)
    participant2 = MagicMock(id="id-2", position=10)
    current_participants = [participant1, participant2]

    participant_data = [
        {"mention": "@user1", "position": 100},
        {"mention": "placeholder", "position": 200},
    ]

    game_service._update_participant_positions(current_participants, participant_data)

    assert participant1.position == 5
    assert participant2.position == 10


def test_update_participant_positions_partial_updates(game_service):
    """Test that only specified participants are updated."""
    participant1 = MagicMock(id="id-1", position=5)
    participant2 = MagicMock(id="id-2", position=10)
    participant3 = MagicMock(id="id-3", position=15)
    current_participants = [participant1, participant2, participant3]

    participant_data = [
        {"participant_id": "id-1", "position": 100},
        {"participant_id": "id-3", "position": 300},
    ]

    game_service._update_participant_positions(current_participants, participant_data)

    assert participant1.position == 100
    assert participant2.position == 10
    assert participant3.position == 300


def test_update_participant_positions_uses_default_position(game_service):
    """Test that position defaults to 0 when not provided."""
    participant1 = MagicMock(id="id-1", position=5)
    current_participants = [participant1]

    participant_data = [
        {"participant_id": "id-1"},
    ]

    game_service._update_participant_positions(current_participants, participant_data)

    assert participant1.position == 0


def test_update_participant_positions_empty_data(game_service):
    """Test that no changes occur with empty participant data."""
    participant1 = MagicMock(id="id-1", position=5)
    participant2 = MagicMock(id="id-2", position=10)
    current_participants = [participant1, participant2]

    participant_data = []

    game_service._update_participant_positions(current_participants, participant_data)

    assert participant1.position == 5
    assert participant2.position == 10


# Tests for update_game helper methods


def test_capture_old_state(game_service):
    """Test capturing participant state before updates."""
    user1 = user_model.User(id=str(uuid.uuid4()), discord_id="user1")
    user2 = user_model.User(id=str(uuid.uuid4()), discord_id="user2")

    participant1 = participant_model.GameParticipant(
        id="p1",
        game_session_id="game1",
        user_id=user1.id,
        user=user1,
        display_name="User 1",
        position=0,
        position_type=ParticipantType.SELF_ADDED,
        joined_at=datetime.datetime.now(UTC),
    )
    participant2 = participant_model.GameParticipant(
        id="p2",
        game_session_id="game1",
        user_id=user2.id,
        user=user2,
        display_name="User 2",
        position=1,
        position_type=ParticipantType.SELF_ADDED,
        joined_at=datetime.datetime.now(UTC),
    )

    game = game_model.GameSession(
        id="game1",
        max_players=2,
        participants=[participant1, participant2],
    )

    old_max_players, old_snapshot, old_partitioned = game_service._capture_old_state(game)

    assert old_max_players == 2
    assert len(old_snapshot) == 2
    assert old_snapshot[0].id == "p1"
    assert old_snapshot[1].id == "p2"
    assert len(old_partitioned.confirmed) == 2


def test_capture_old_state_with_unlimited_players(game_service):
    """Test capturing state with unlimited players (None max_players)."""
    user1 = user_model.User(id=str(uuid.uuid4()), discord_id="user1")

    participant1 = participant_model.GameParticipant(
        id="p1",
        game_session_id="game1",
        user_id=user1.id,
        user=user1,
        display_name="User 1",
        position=0,
        position_type=ParticipantType.SELF_ADDED,
        joined_at=datetime.datetime.now(UTC),
    )

    game = game_model.GameSession(
        id="game1",
        max_players=None,
        participants=[participant1],
    )

    old_max_players, old_snapshot, old_partitioned = game_service._capture_old_state(game)

    assert old_max_players == DEFAULT_MAX_PLAYERS
    assert len(old_snapshot) == 1


@pytest.mark.asyncio
async def test_update_image_fields_sets_thumbnail(game_service):
    """Test setting thumbnail data."""
    game = game_model.GameSession(
        id="game1",
        thumbnail_id=None,
    )

    thumbnail_id = uuid.uuid4()
    with (
        patch("services.api.services.games.store_image", new_callable=AsyncMock) as mock_store,
        patch("services.api.services.games.release_image", new_callable=AsyncMock) as mock_release,
    ):
        mock_store.return_value = thumbnail_id

        await game_service._update_image_fields(
            game,
            thumbnail_data=b"thumbnail_bytes",
            thumbnail_mime_type="image/png",
            image_data=None,
            image_mime_type=None,
        )

    assert game.thumbnail_id == thumbnail_id
    mock_store.assert_called_once()
    mock_release.assert_called_once_with(game_service.db, None)


@pytest.mark.asyncio
async def test_update_image_fields_removes_thumbnail(game_service):
    """Test removing thumbnail by passing empty bytes."""
    existing_id = uuid.uuid4()
    game = game_model.GameSession(
        id="game1",
        thumbnail_id=existing_id,
    )

    with patch("services.api.services.games.release_image", new_callable=AsyncMock) as mock_release:
        await game_service._update_image_fields(
            game,
            thumbnail_data=b"",
            thumbnail_mime_type="",
            image_data=None,
            image_mime_type=None,
        )

    assert game.thumbnail_id is None
    mock_release.assert_called_once_with(game_service.db, existing_id)


@pytest.mark.asyncio
async def test_update_image_fields_sets_banner(game_service):
    """Test setting banner image data."""
    game = game_model.GameSession(
        id="game1",
        banner_image_id=None,
    )

    banner_id = uuid.uuid4()
    with (
        patch("services.api.services.games.store_image", new_callable=AsyncMock) as mock_store,
        patch("services.api.services.games.release_image", new_callable=AsyncMock) as mock_release,
    ):
        mock_store.return_value = banner_id

        await game_service._update_image_fields(
            game,
            thumbnail_data=None,
            thumbnail_mime_type=None,
            image_data=b"image_bytes",
            image_mime_type="image/jpeg",
        )

    assert game.banner_image_id == banner_id
    mock_store.assert_called_once()
    mock_release.assert_called_once_with(game_service.db, None)


@pytest.mark.asyncio
async def test_update_image_fields_removes_banner(game_service):
    """Test removing banner image by passing empty bytes."""
    existing_id = uuid.uuid4()
    game = game_model.GameSession(
        id="game1",
        banner_image_id=existing_id,
    )

    with patch("services.api.services.games.release_image", new_callable=AsyncMock) as mock_release:
        await game_service._update_image_fields(
            game,
            thumbnail_data=None,
            thumbnail_mime_type=None,
            image_data=b"",
            image_mime_type="",
        )

    assert game.banner_image_id is None
    mock_release.assert_called_once_with(game_service.db, existing_id)


@pytest.mark.asyncio
async def test_update_image_fields_no_changes(game_service):
    """Test that passing None for all images makes no changes."""
    thumb_id = uuid.uuid4()
    banner_id = uuid.uuid4()
    game = game_model.GameSession(
        id="game1",
        thumbnail_id=thumb_id,
        banner_image_id=banner_id,
    )

    with (
        patch("services.api.services.games.store_image", new_callable=AsyncMock) as mock_store,
        patch("services.api.services.games.release_image", new_callable=AsyncMock) as mock_release,
    ):
        await game_service._update_image_fields(
            game,
            thumbnail_data=None,
            thumbnail_mime_type=None,
            image_data=None,
            image_mime_type=None,
        )

    # No changes should be made
    assert game.thumbnail_id == thumb_id
    assert game.banner_image_id == banner_id
    mock_store.assert_not_called()
    mock_release.assert_not_called()


@pytest.mark.asyncio
async def test_process_game_update_schedules_both_flags(game_service, mock_db):
    """Test updating both notification and status schedules."""
    game = game_model.GameSession(
        id="game1",
        reminder_minutes=[30, 10],
        scheduled_at=datetime.datetime(2026, 1, 20, 10, 0, tzinfo=UTC),
        expected_duration_minutes=120,
    )

    with patch(
        "services.api.services.games.notification_schedule_service.NotificationScheduleService"
    ) as mock_schedule_service_class:
        mock_schedule_service = AsyncMock()
        mock_schedule_service.update_schedule = AsyncMock()
        mock_schedule_service_class.return_value = mock_schedule_service

        with patch.object(game_service, "_update_status_schedules", new=AsyncMock()) as mock_status:
            await game_service._process_game_update_schedules(
                game, schedule_needs_update=True, status_schedule_needs_update=True
            )

            mock_schedule_service.update_schedule.assert_called_once_with(game, [30, 10])
            mock_status.assert_called_once_with(game)


@pytest.mark.asyncio
async def test_process_game_update_schedules_only_notification(game_service, mock_db):
    """Test updating only notification schedule."""
    game = game_model.GameSession(
        id="game1",
        reminder_minutes=None,
        scheduled_at=datetime.datetime(2026, 1, 20, 10, 0, tzinfo=UTC),
    )

    with patch(
        "services.api.services.games.notification_schedule_service.NotificationScheduleService"
    ) as mock_schedule_service_class:
        mock_schedule_service = AsyncMock()
        mock_schedule_service.update_schedule = AsyncMock()
        mock_schedule_service_class.return_value = mock_schedule_service

        with patch.object(game_service, "_update_status_schedules", new=AsyncMock()) as mock_status:
            await game_service._process_game_update_schedules(
                game, schedule_needs_update=True, status_schedule_needs_update=False
            )

            mock_schedule_service.update_schedule.assert_called_once_with(game, [60, 15])
            mock_status.assert_not_called()


@pytest.mark.asyncio
async def test_process_game_update_schedules_only_status(game_service, mock_db):
    """Test updating only status schedule."""
    game = game_model.GameSession(
        id="game1",
        scheduled_at=datetime.datetime(2026, 1, 20, 10, 0, tzinfo=UTC),
        expected_duration_minutes=90,
    )

    with patch(
        "services.api.services.games.notification_schedule_service.NotificationScheduleService"
    ) as mock_schedule_service_class:
        mock_schedule_service = AsyncMock()
        mock_schedule_service_class.return_value = mock_schedule_service

        with patch.object(game_service, "_update_status_schedules", new=AsyncMock()) as mock_status:
            await game_service._process_game_update_schedules(
                game, schedule_needs_update=False, status_schedule_needs_update=True
            )

            mock_schedule_service.update_schedule.assert_not_called()
            mock_status.assert_called_once_with(game)


@pytest.mark.asyncio
async def test_process_game_update_schedules_neither(game_service, mock_db):
    """Test with no schedule updates needed."""
    game = game_model.GameSession(id="game1")

    with patch(
        "services.api.services.games.notification_schedule_service.NotificationScheduleService"
    ) as mock_schedule_service_class:
        mock_schedule_service = AsyncMock()
        mock_schedule_service_class.return_value = mock_schedule_service

        with patch.object(game_service, "_update_status_schedules", new=AsyncMock()) as mock_status:
            await game_service._process_game_update_schedules(
                game, schedule_needs_update=False, status_schedule_needs_update=False
            )

            mock_schedule_service.update_schedule.assert_not_called()
            mock_status.assert_not_called()


@pytest.mark.asyncio
async def test_detect_and_notify_promotions_with_promotions(game_service):
    """Test detecting and notifying promoted users."""
    user1 = user_model.User(id=str(uuid.uuid4()), discord_id="user1")
    user2 = user_model.User(id=str(uuid.uuid4()), discord_id="user2")
    user3 = user_model.User(id=str(uuid.uuid4()), discord_id="user3")

    # Create old state with 2 confirmed, 1 overflow
    old_participants = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p2",
            game_session_id="game1",
            user_id=user2.id,
            user=user2,
            position=1,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p3",
            game_session_id="game1",
            user_id=user3.id,
            user=user3,
            position=2,
            position_type=ParticipantType.SELF_ADDED,
        ),
    ]

    old_partitioned = partition_participants(old_participants, 2)

    # New state: max_players increased to 3, all confirmed
    game = game_model.GameSession(
        id="game1",
        max_players=3,
        participants=old_participants,
    )

    with patch.object(game_service, "_notify_promoted_users", new=AsyncMock()) as mock_notify:
        await game_service._detect_and_notify_promotions(game, old_partitioned)

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert call_args[1]["game"] == game
        assert "user3" in call_args[1]["promoted_discord_ids"]


@pytest.mark.asyncio
async def test_detect_and_notify_promotions_no_promotions(game_service):
    """Test with no promotions detected."""
    user1 = user_model.User(id=str(uuid.uuid4()), discord_id="user1")
    user2 = user_model.User(id=str(uuid.uuid4()), discord_id="user2")

    old_participants = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p2",
            game_session_id="game1",
            user_id=user2.id,
            user=user2,
            position=1,
            position_type=ParticipantType.SELF_ADDED,
        ),
    ]

    old_partitioned = partition_participants(old_participants, 2)

    game = game_model.GameSession(
        id="game1",
        max_players=2,
        participants=old_participants,
    )

    with patch.object(game_service, "_notify_promoted_users", new=AsyncMock()) as mock_notify:
        await game_service._detect_and_notify_promotions(game, old_partitioned)

        mock_notify.assert_not_called()


# ==============================================================================
# Helper Method Tests: _resolve_game_host Extraction (Phase 2 Task 2.1)
# ==============================================================================


@pytest.mark.asyncio
async def test_verify_bot_manager_permission_success(
    game_service,
    mock_db,
):
    """Test successful bot manager permission verification."""
    user_id = str(uuid.uuid4())
    guild_id = "guild123"
    access_token = "token123"

    user = user_model.User(id=user_id, discord_id="discord123")

    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user))
    )

    mock_role_service = MagicMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    with patch(
        "services.api.services.games.roles_module.get_role_service",
        return_value=mock_role_service,
    ):
        await game_service._verify_bot_manager_permission(
            user_id,
            guild_id,
            access_token,
        )

        mock_role_service.check_bot_manager_permission.assert_called_once_with(
            "discord123",
            guild_id,
            mock_db,
            access_token,
        )


@pytest.mark.asyncio
async def test_verify_bot_manager_permission_user_not_found(
    game_service,
    mock_db,
):
    """Test permission check with non-existent user."""
    user_id = str(uuid.uuid4())
    guild_id = "guild123"
    access_token = "token123"

    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )

    with pytest.raises(ValueError, match="Requester user not found"):
        await game_service._verify_bot_manager_permission(
            user_id,
            guild_id,
            access_token,
        )


@pytest.mark.asyncio
async def test_verify_bot_manager_permission_not_manager(
    game_service,
    mock_db,
):
    """Test permission check with non-manager user."""
    user_id = str(uuid.uuid4())
    guild_id = "guild123"
    access_token = "token123"

    user = user_model.User(id=user_id, discord_id="discord123")

    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user))
    )

    mock_role_service = MagicMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=False)

    with (
        patch(
            "services.api.services.games.roles_module.get_role_service",
            return_value=mock_role_service,
        ),
        pytest.raises(ValueError, match="Only bot managers can specify the game host"),
    ):
        await game_service._verify_bot_manager_permission(
            user_id,
            guild_id,
            access_token,
        )


@pytest.mark.asyncio
async def test_resolve_and_validate_host_participant_success(game_service):
    """Test successful host participant resolution."""
    host_mention = "@testuser"
    guild_id = "guild123"
    access_token = "token123"

    resolved_host = {
        "type": "discord",
        "discord_id": "discord123",
        "display_name": "Test User",
    }

    game_service.participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=([resolved_host], [])
    )

    result = await game_service._resolve_and_validate_host_participant(
        host_mention,
        guild_id,
        access_token,
    )

    assert result == resolved_host


@pytest.mark.asyncio
async def test_resolve_and_validate_host_participant_validation_error(game_service):
    """Test host resolution with validation errors."""
    host_mention = "@invaliduser"
    guild_id = "guild123"
    access_token = "token123"

    validation_error = {
        "input": host_mention,
        "reason": "User not found",
        "suggestions": [],
    }

    game_service.participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=([], [validation_error])
    )

    with pytest.raises(resolver_module.ValidationError):
        await game_service._resolve_and_validate_host_participant(
            host_mention,
            guild_id,
            access_token,
        )


@pytest.mark.asyncio
async def test_resolve_and_validate_host_participant_no_results(game_service):
    """Test host resolution with no results."""
    host_mention = "@testuser"
    guild_id = "guild123"
    access_token = "token123"

    game_service.participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=([], [])
    )

    with pytest.raises(ValueError, match="Could not resolve host"):
        await game_service._resolve_and_validate_host_participant(
            host_mention,
            guild_id,
            access_token,
        )


@pytest.mark.asyncio
async def test_resolve_and_validate_host_participant_placeholder(game_service):
    """Test host resolution rejecting placeholder participants."""
    host_mention = "Placeholder Name"
    guild_id = "guild123"
    access_token = "token123"

    resolved_host = {
        "type": "placeholder",
        "display_name": "Placeholder Name",
    }

    game_service.participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=([resolved_host], [])
    )

    with pytest.raises(resolver_module.ValidationError) as exc_info:
        await game_service._resolve_and_validate_host_participant(
            host_mention,
            guild_id,
            access_token,
        )

    assert exc_info.value.invalid_mentions[0]["reason"] == (
        "Game host must be a Discord user (use @username format). "
        "Placeholder strings are not allowed for the host field."
    )


@pytest.mark.asyncio
async def test_get_or_create_user_by_discord_id_existing(
    game_service,
    mock_db,
):
    """Test retrieving existing user by Discord ID."""
    discord_id = "discord123"
    existing_user = user_model.User(
        id=str(uuid.uuid4()),
        discord_id=discord_id,
    )

    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_user))
    )

    result = await game_service._get_or_create_user_by_discord_id(discord_id)

    assert result == existing_user
    mock_db.add.assert_not_called()
    mock_db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_user_by_discord_id_new(
    game_service,
    mock_db,
):
    """Test creating new user for Discord ID."""
    discord_id = "discord123"

    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    mock_db.flush = AsyncMock()

    result = await game_service._get_or_create_user_by_discord_id(discord_id)

    assert result.discord_id == discord_id
    assert result.id is not None
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
