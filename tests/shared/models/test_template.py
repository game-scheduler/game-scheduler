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


"""Tests for GameTemplate model."""

from sqlalchemy import inspect

from shared.models.base import utc_now
from shared.models.template import GameTemplate


def test_game_template_has_required_columns():
    """Verify GameTemplate model has all required columns."""
    mapper = inspect(GameTemplate)
    column_names = {col.key for col in mapper.columns}

    required_columns = {
        "id",
        "guild_id",
        "name",
        "description",
        "order",
        "is_default",
        "channel_id",
        "notify_role_ids",
        "allowed_player_role_ids",
        "allowed_host_role_ids",
        "max_players",
        "expected_duration_minutes",
        "reminder_minutes",
        "where",
        "signup_instructions",
        "created_at",
        "updated_at",
    }

    assert required_columns.issubset(column_names)


def test_game_template_has_relationships():
    """Verify GameTemplate model has required relationships."""
    mapper = inspect(GameTemplate)
    relationship_names = {rel.key for rel in mapper.relationships}

    assert "guild" in relationship_names
    assert "channel" in relationship_names
    assert "games" in relationship_names


def test_game_template_table_name():
    """Verify GameTemplate uses correct table name."""
    assert GameTemplate.__tablename__ == "game_templates"


def test_game_template_instantiation():
    """Verify GameTemplate can be instantiated with required fields."""
    now = utc_now()
    template = GameTemplate(
        id="test-id",
        guild_id="guild-id",
        name="Test Template",
        channel_id="channel-id",
        is_default=True,
        order=0,
        created_at=now,
        updated_at=now,
    )

    assert template.id == "test-id"
    assert template.guild_id == "guild-id"
    assert template.name == "Test Template"
    assert template.channel_id == "channel-id"
    assert template.is_default is True
    assert template.order == 0


def test_game_template_optional_fields():
    """Verify GameTemplate handles optional fields correctly."""
    now = utc_now()
    template = GameTemplate(
        id="test-id",
        guild_id="guild-id",
        name="Test Template",
        channel_id="channel-id",
        order=0,
        created_at=now,
        updated_at=now,
        description="Test description",
        max_players=10,
        expected_duration_minutes=120,
        reminder_minutes=[60, 15],
        where="Discord Voice Channel",
        signup_instructions="Join the voice channel",
        notify_role_ids=["role1", "role2"],
        allowed_player_role_ids=["role3"],
        allowed_host_role_ids=["role4"],
    )

    assert template.description == "Test description"
    assert template.max_players == 10
    assert template.expected_duration_minutes == 120
    assert template.reminder_minutes == [60, 15]
    assert template.where == "Discord Voice Channel"
    assert template.signup_instructions == "Join the voice channel"
    assert template.notify_role_ids == ["role1", "role2"]
    assert template.allowed_player_role_ids == ["role3"]
    assert template.allowed_host_role_ids == ["role4"]


def test_game_template_repr():
    """Verify GameTemplate __repr__ method."""
    now = utc_now()
    template = GameTemplate(
        id="test-id",
        guild_id="guild-id",
        name="Test Template",
        channel_id="channel-id",
        order=0,
        created_at=now,
        updated_at=now,
    )

    repr_str = repr(template)
    assert "GameTemplate" in repr_str
    assert "test-id" in repr_str
    assert "Test Template" in repr_str
    assert "guild-id" in repr_str


def test_game_template_has_indexes():
    """Verify GameTemplate has required indexes."""
    table = GameTemplate.__table__
    index_names = {idx.name for idx in table.indexes}

    assert "ix_game_templates_guild_id" in index_names
    assert "ix_game_templates_guild_order" in index_names
    assert "ix_game_templates_guild_default" in index_names


def test_game_template_has_check_constraint():
    """Verify GameTemplate has order >= 0 check constraint."""
    table = GameTemplate.__table__
    constraint_names = {const.name for const in table.constraints if hasattr(const, "name")}

    assert "ck_template_order_positive" in constraint_names
