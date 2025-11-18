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


"""Tests for configuration service and settings inheritance."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.services import config
from shared.models import channel, game, guild


@pytest.fixture
def mock_db():
    """Create mock async database session."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def sample_guild():
    """Create sample guild configuration."""
    return guild.GuildConfiguration(
        id=str(uuid.uuid4()),
        guild_id="123456789",
        guild_name="Test Guild",
        default_max_players=10,
        default_reminder_minutes=[60, 15],
        default_rules="Default guild rules",
        allowed_host_role_ids=["role1", "role2"],
        require_host_role=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_channel():
    """Create sample channel configuration."""
    guild_id = str(uuid.uuid4())
    return channel.ChannelConfiguration(
        id=str(uuid.uuid4()),
        guild_id=guild_id,
        channel_id="987654321",
        channel_name="Test Channel",
        is_active=True,
        max_players=8,
        reminder_minutes=[30, 10],
        default_rules="Channel rules",
        allowed_host_role_ids=["role3"],
        game_category="D&D",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_game():
    """Create sample game session."""
    return game.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.utcnow(),
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
        host_id=str(uuid.uuid4()),
        max_players=6,
        reminder_minutes=[45],
        rules="Game rules",
        status="SCHEDULED",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestSettingsResolver:
    """Test settings inheritance resolution."""

    def test_resolve_max_players_game_override(self, sample_game, sample_channel, sample_guild):
        """Game-level max players overrides channel and guild."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_max_players(sample_game, sample_channel, sample_guild)
        assert result == 6

    def test_resolve_max_players_channel_override(self, sample_channel, sample_guild):
        """Channel-level max players overrides guild."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_max_players(None, sample_channel, sample_guild)
        assert result == 8

    def test_resolve_max_players_guild_default(self, sample_guild):
        """Guild-level max players is fallback."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_max_players(None, None, sample_guild)
        assert result == 10

    def test_resolve_max_players_system_default(self):
        """System default when no config set."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_max_players(None, None, None)
        assert result == 10

    def test_resolve_reminder_minutes_game_override(
        self, sample_game, sample_channel, sample_guild
    ):
        """Game-level reminders override channel and guild."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_reminder_minutes(sample_game, sample_channel, sample_guild)
        assert result == [45]

    def test_resolve_reminder_minutes_channel_override(self, sample_channel, sample_guild):
        """Channel-level reminders override guild."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_reminder_minutes(None, sample_channel, sample_guild)
        assert result == [30, 10]

    def test_resolve_reminder_minutes_guild_default(self, sample_guild):
        """Guild-level reminders are fallback."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_reminder_minutes(None, None, sample_guild)
        assert result == [60, 15]

    def test_resolve_reminder_minutes_system_default(self):
        """System default reminders when no config set."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_reminder_minutes(None, None, None)
        assert result == [60, 15]

    def test_resolve_rules_game_override(self, sample_game, sample_channel, sample_guild):
        """Game-level rules override channel and guild."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_rules(sample_game, sample_channel, sample_guild)
        assert result == "Game rules"

    def test_resolve_rules_channel_override(self, sample_channel, sample_guild):
        """Channel-level rules override guild."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_rules(None, sample_channel, sample_guild)
        assert result == "Channel rules"

    def test_resolve_rules_guild_default(self, sample_guild):
        """Guild-level rules are fallback."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_rules(None, None, sample_guild)
        assert result == "Default guild rules"

    def test_resolve_rules_empty_default(self):
        """Empty string when no rules configured."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_rules(None, None, None)
        assert result == ""

    def test_resolve_allowed_host_roles_channel_override(self, sample_channel, sample_guild):
        """Channel-level roles override guild."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_allowed_host_roles(sample_channel, sample_guild)
        assert result == ["role3"]

    def test_resolve_allowed_host_roles_guild_default(self, sample_guild):
        """Guild-level roles are fallback."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_allowed_host_roles(None, sample_guild)
        assert result == ["role1", "role2"]

    def test_resolve_allowed_host_roles_empty_default(self):
        """Empty list when no roles configured."""
        resolver = config.SettingsResolver()
        result = resolver.resolve_allowed_host_roles(None, None)
        assert result == []


class TestConfigurationService:
    """Test configuration service database operations."""

    @pytest.mark.asyncio
    async def test_create_guild_config(self, mock_db):
        """Create guild configuration successfully."""
        service = config.ConfigurationService(mock_db)

        result = await service.create_guild_config(
            guild_discord_id="123456789",
            guild_name="Test Guild",
            default_max_players=10,
            default_reminder_minutes=[60, 15],
        )

        assert mock_db.add.called
        assert mock_db.commit.called
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_guild_by_discord_id(self, mock_db, sample_guild):
        """Fetch guild by Discord ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_guild
        mock_db.execute.return_value = mock_result

        service = config.ConfigurationService(mock_db)
        result = await service.get_guild_by_discord_id("123456789")

        assert result == sample_guild
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_get_guild_by_discord_id_not_found(self, mock_db):
        """Return None when guild not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = config.ConfigurationService(mock_db)
        result = await service.get_guild_by_discord_id("999999999")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_channel_config(self, mock_db):
        """Create channel configuration successfully."""
        service = config.ConfigurationService(mock_db)

        result = await service.create_channel_config(
            guild_id=str(uuid.uuid4()),
            channel_discord_id="987654321",
            channel_name="Test Channel",
            is_active=True,
        )

        assert mock_db.add.called
        assert mock_db.commit.called
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_channel_by_discord_id(self, mock_db, sample_channel):
        """Fetch channel by Discord ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_channel
        mock_db.execute.return_value = mock_result

        service = config.ConfigurationService(mock_db)
        result = await service.get_channel_by_discord_id("987654321")

        assert result == sample_channel
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_get_channels_by_guild(self, mock_db, sample_channel):
        """Fetch all channels for a guild."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_channel]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        service = config.ConfigurationService(mock_db)
        guild_id = str(uuid.uuid4())
        result = await service.get_channels_by_guild(guild_id)

        assert len(result) == 1
        assert result[0] == sample_channel

    @pytest.mark.asyncio
    async def test_update_guild_config(self, mock_db, sample_guild):
        """Update guild configuration."""
        service = config.ConfigurationService(mock_db)

        await service.update_guild_config(
            sample_guild, guild_name="Updated Guild", default_max_players=12
        )

        assert mock_db.commit.called
        assert mock_db.refresh.called

    @pytest.mark.asyncio
    async def test_update_channel_config(self, mock_db, sample_channel):
        """Update channel configuration."""
        service = config.ConfigurationService(mock_db)

        await service.update_channel_config(
            sample_channel, channel_name="Updated Channel", is_active=False
        )

        assert mock_db.commit.called
        assert mock_db.refresh.called
