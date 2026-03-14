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


"""Unit tests for init service seed_e2e module helpers."""

from unittest.mock import Mock, patch

from services.init.seed_e2e import (
    GuildConfig,
    _create_guild_entities,
    _guild_exists,
    _validate_e2e_config,
)


class TestValidateE2EConfig:
    """Tests for _validate_e2e_config helper."""

    @patch("services.init.seed_e2e.os.getenv")
    @patch("services.init.seed_e2e.logger")
    def test_returns_none_when_test_environment_not_enabled(self, mock_logger, mock_getenv):
        """Should return None when TEST_ENVIRONMENT is not 'true'."""
        mock_getenv.return_value = "false"

        result = _validate_e2e_config()

        assert result is None
        mock_logger.info.assert_called_once()

    @patch("services.init.seed_e2e.os.getenv")
    @patch("services.init.seed_e2e.logger")
    def test_returns_none_when_env_vars_missing(self, mock_logger, mock_getenv):
        """Should return None when required environment variables are missing."""

        def getenv_side_effect(key):
            env_vars = {
                "TEST_ENVIRONMENT": "true",
                "DISCORD_GUILD_A_ID": "123",
                "DISCORD_GUILD_A_CHANNEL_ID": None,  # Missing!
            }
            return env_vars.get(key)

        mock_getenv.side_effect = getenv_side_effect

        result = _validate_e2e_config()

        assert result is None
        mock_logger.warning.assert_called_once()

    @patch("services.init.seed_e2e.os.getenv")
    def test_returns_config_when_all_vars_present(self, mock_getenv):
        """Should return E2EConfig when all environment variables are present."""

        def getenv_side_effect(key):
            env_vars = {
                "TEST_ENVIRONMENT": "true",
                "DISCORD_GUILD_A_ID": "guild_a_123",
                "DISCORD_GUILD_A_CHANNEL_ID": "channel_a_456",
                "DISCORD_USER_ID": "user_789",
                "DISCORD_ADMIN_BOT_A_TOKEN": "bot_token_abc",
                "DISCORD_GUILD_B_ID": "guild_b_234",
                "DISCORD_GUILD_B_CHANNEL_ID": "channel_b_567",
                "DISCORD_ADMIN_BOT_B_CLIENT_ID": "bot_b_890",
            }
            return env_vars.get(key)

        mock_getenv.side_effect = getenv_side_effect

        result = _validate_e2e_config()

        assert result is not None
        assert result.guild_a_id == "guild_a_123"
        assert result.channel_a_id == "channel_a_456"
        assert result.user_id == "user_789"
        assert result.bot_token == "bot_token_abc"
        assert result.guild_b_id == "guild_b_234"
        assert result.channel_b_id == "channel_b_567"
        assert result.user_b_id == "bot_b_890"


class TestGuildExists:
    """Tests for _guild_exists helper."""

    def test_returns_true_when_guild_found(self):
        """Should return True when guild exists in database."""
        mock_session = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = {"id": "guild-uuid"}
        mock_session.execute.return_value = mock_result

        result = _guild_exists(mock_session, "123456789")

        assert result is True
        mock_session.execute.assert_called_once()

    def test_returns_false_when_guild_not_found(self):
        """Should return False when guild does not exist in database."""
        mock_session = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        result = _guild_exists(mock_session, "987654321")

        assert result is False
        mock_session.execute.assert_called_once()


class TestCreateGuildEntities:
    """Tests for _create_guild_entities helper."""

    @patch("services.init.seed_e2e.datetime")
    @patch("services.init.seed_e2e.uuid4")
    @patch("services.init.seed_e2e.logger")
    def test_creates_guild_channel_template_and_user(self, mock_logger, mock_uuid4, mock_datetime):
        """Should insert guild, channel, template, and user entities."""
        mock_uuid4.side_effect = [
            "guild-id",
            "channel-config-id",
            "template-id",
            "user-id",
        ]
        mock_now = Mock()
        mock_datetime.now.return_value = Mock(replace=Mock(return_value=mock_now))

        mock_session = Mock()
        guild_config = GuildConfig(
            guild_id="discord-guild-123",
            channel_id="discord-channel-456",
            user_id="discord-user-789",
            guild_name="Test Guild",
        )

        _create_guild_entities(mock_session, guild_config)

        assert mock_session.execute.call_count == 4
        mock_logger.info.assert_called_once_with("Created guild entities for %s", "Test Guild")

    @patch("services.init.seed_e2e.datetime")
    @patch("services.init.seed_e2e.uuid4")
    @patch("services.init.seed_e2e.logger")
    def test_creates_additional_bot_user_when_provided(
        self, mock_logger, mock_uuid4, mock_datetime
    ):
        """Should insert bot user when bot_id parameter is provided."""
        mock_uuid4.side_effect = [
            "guild-id",
            "channel-config-id",
            "template-id",
            "user-id",
            "bot-user-id",
        ]
        mock_now = Mock()
        mock_datetime.now.return_value = Mock(replace=Mock(return_value=mock_now))

        mock_session = Mock()
        guild_config = GuildConfig(
            guild_id="discord-guild-123",
            channel_id="discord-channel-456",
            user_id="discord-user-789",
            guild_name="Test Guild",
        )

        _create_guild_entities(mock_session, guild_config, bot_id="bot-discord-id")

        assert mock_session.execute.call_count == 5

    @patch("services.init.seed_e2e.datetime")
    @patch("services.init.seed_e2e.uuid4")
    def test_uses_guild_config_values_in_inserts(self, mock_uuid4, mock_datetime):
        """Should use values from GuildConfig in database inserts."""
        mock_uuid4.side_effect = [
            "guild-id",
            "channel-config-id",
            "template-id",
            "user-id",
        ]
        mock_now = Mock()
        mock_datetime.now.return_value = Mock(replace=Mock(return_value=mock_now))

        mock_session = Mock()
        guild_config = GuildConfig(
            guild_id="specific-guild-id",
            channel_id="specific-channel-id",
            user_id="specific-user-id",
            guild_name="Specific Guild Name",
        )

        _create_guild_entities(mock_session, guild_config)

        execute_calls = mock_session.execute.call_args_list
        guild_insert_sql = str(execute_calls[0][0][0])
        assert "guild_configurations" in guild_insert_sql

        guild_insert_params = execute_calls[0][0][1]
        assert guild_insert_params["guild_id"] == "specific-guild-id"

        channel_insert_params = execute_calls[1][0][1]
        assert channel_insert_params["channel_id"] == "specific-channel-id"

        template_insert_params = execute_calls[2][0][1]
        assert "Specific Guild Name" in template_insert_params["name"]
        # Verify template references the channel_configurations record ID (foreign key)
        assert template_insert_params["channel_id"] == channel_insert_params["id"]

        user_insert_params = execute_calls[3][0][1]
        assert user_insert_params["discord_id"] == "specific-user-id"
