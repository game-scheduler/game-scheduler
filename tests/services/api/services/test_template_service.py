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


"""Tests for template service."""

from unittest.mock import AsyncMock, Mock

import pytest

from services.api.services.template_service import TemplateService
from shared.models.template import GameTemplate


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def template_service(mock_db):
    """Create template service with mock db."""
    return TemplateService(mock_db)


@pytest.fixture
def sample_template():
    """Create sample template."""
    return GameTemplate(
        id="template-uuid-1",
        guild_id="guild-uuid-1",
        name="D&D Campaign",
        description="Weekly D&D session",
        channel_id="channel-uuid-1",
        order=1,
        is_default=False,
        allowed_host_role_ids=["role1", "role2"],
        max_players=6,
        expected_duration_minutes=180,
        reminder_minutes=[60, 15],
    )


@pytest.mark.asyncio
async def test_get_templates_for_user_admin(template_service, mock_db, sample_template):
    """Test getting templates for admin user (no filtering)."""
    default_template = GameTemplate(
        id="template-uuid-default",
        guild_id="guild-uuid-1",
        name="Default",
        is_default=True,
        channel_id="channel-uuid-1",
        order=0,
    )

    mock_scalars = Mock()
    mock_scalars.all.return_value = [default_template, sample_template]
    mock_result = Mock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    templates = await template_service.get_templates_for_user(
        guild_id="guild-uuid-1",
        user_role_ids=["role3"],
        is_admin=True,
    )

    assert len(templates) == 2
    assert templates[0].is_default is True
    assert templates[1].name == "D&D Campaign"


@pytest.mark.asyncio
async def test_get_templates_for_user_with_role_filtering(
    template_service, mock_db, sample_template
):
    """Test getting templates with role filtering for non-admin."""
    mock_scalars = Mock()
    mock_scalars.all.return_value = [sample_template]
    mock_result = Mock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    templates = await template_service.get_templates_for_user(
        guild_id="guild-uuid-1",
        user_role_ids=["role1"],
        is_admin=False,
    )

    assert len(templates) == 1
    assert templates[0].name == "D&D Campaign"


@pytest.mark.asyncio
async def test_get_templates_for_user_no_matching_roles(template_service, mock_db, sample_template):
    """Test getting templates with no matching roles."""
    mock_scalars = Mock()
    mock_scalars.all.return_value = [sample_template]
    mock_result = Mock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    templates = await template_service.get_templates_for_user(
        guild_id="guild-uuid-1",
        user_role_ids=["role3"],
        is_admin=False,
    )

    assert len(templates) == 0


@pytest.mark.asyncio
async def test_get_templates_for_user_empty_allowed_roles(template_service, mock_db):
    """Test that templates with empty allowed_host_role_ids are visible to everyone."""
    public_template = GameTemplate(
        id="template-uuid-public",
        guild_id="guild-uuid-1",
        name="Public Template",
        channel_id="channel-uuid-1",
        order=1,
        is_default=False,
        allowed_host_role_ids=None,
    )

    mock_scalars = Mock()
    mock_scalars.all.return_value = [public_template]
    mock_result = Mock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    templates = await template_service.get_templates_for_user(
        guild_id="guild-uuid-1",
        user_role_ids=["any-role"],
        is_admin=False,
    )

    assert len(templates) == 1
    assert templates[0].name == "Public Template"


@pytest.mark.asyncio
async def test_get_template_by_id(template_service, mock_db, sample_template):
    """Test getting template by ID."""
    mock_db.get.return_value = sample_template

    template = await template_service.get_template_by_id("template-uuid-1")

    assert template.id == "template-uuid-1"
    assert template.name == "D&D Campaign"
    mock_db.get.assert_awaited_once_with(GameTemplate, "template-uuid-1")


@pytest.mark.asyncio
async def test_create_template(template_service, mock_db):
    """Test creating a new template."""
    await template_service.create_template(
        guild_id="guild-uuid-1",
        channel_id="channel-uuid-1",
        name="New Template",
        description="Test template",
        order=2,
        max_players=8,
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()

    added_template = mock_db.add.call_args[0][0]
    assert isinstance(added_template, GameTemplate)
    assert added_template.guild_id == "guild-uuid-1"
    assert added_template.channel_id == "channel-uuid-1"
    assert added_template.name == "New Template"
    assert added_template.description == "Test template"
    assert added_template.order == 2
    assert added_template.max_players == 8


@pytest.mark.asyncio
async def test_create_default_template(template_service, mock_db):
    """Test creating default template for guild initialization."""
    await template_service.create_default_template(
        guild_id="guild-uuid-1",
        channel_id="channel-uuid-1",
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()

    added_template = mock_db.add.call_args[0][0]
    assert isinstance(added_template, GameTemplate)
    assert added_template.name == "Default"
    assert added_template.is_default is True
    assert added_template.order == 0


@pytest.mark.asyncio
async def test_update_template(template_service, mock_db, sample_template):
    """Test updating a template."""
    updates = {
        "name": "Updated Name",
        "max_players": 10,
        "description": "Updated description",
    }

    await template_service.update_template(sample_template, **updates)

    assert sample_template.name == "Updated Name"
    assert sample_template.max_players == 10
    assert sample_template.description == "Updated description"
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_template_ignores_none_values(template_service, mock_db, sample_template):
    """Test that update_template ignores None values."""
    original_name = sample_template.name
    updates = {
        "name": None,
        "max_players": 10,
    }

    await template_service.update_template(sample_template, **updates)

    assert sample_template.name == original_name
    assert sample_template.max_players == 10


@pytest.mark.asyncio
async def test_set_default(template_service, mock_db, sample_template):
    """Test setting a template as default."""
    mock_db.get.return_value = sample_template
    mock_execute_result = AsyncMock()
    mock_db.execute.return_value = mock_execute_result

    template = await template_service.set_default("template-uuid-1")

    assert template.is_default is True
    mock_db.execute.assert_awaited_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_default_not_found(template_service, mock_db):
    """Test setting default template when template not found."""
    mock_db.get.return_value = None

    with pytest.raises(ValueError, match="Template not found"):
        await template_service.set_default("nonexistent-id")


@pytest.mark.asyncio
async def test_delete_template(template_service, mock_db, sample_template):
    """Test deleting a non-default template."""
    mock_db.get.return_value = sample_template

    await template_service.delete_template("template-uuid-1")

    mock_db.delete.assert_awaited_once_with(sample_template)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_template_not_found(template_service, mock_db):
    """Test deleting template when not found."""
    mock_db.get.return_value = None

    with pytest.raises(ValueError, match="Template not found"):
        await template_service.delete_template("nonexistent-id")


@pytest.mark.asyncio
async def test_delete_default_template_raises_error(template_service, mock_db):
    """Test that deleting default template raises error."""
    default_template = GameTemplate(
        id="template-uuid-default",
        guild_id="guild-uuid-1",
        name="Default",
        is_default=True,
        channel_id="channel-uuid-1",
        order=0,
    )
    mock_db.get.return_value = default_template

    with pytest.raises(ValueError, match="Cannot delete the default template"):
        await template_service.delete_template("template-uuid-default")

    mock_db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_reorder_templates(template_service, mock_db):
    """Test bulk reordering templates."""
    template1 = GameTemplate(
        id="template-uuid-1",
        guild_id="guild-uuid-1",
        name="Template 1",
        channel_id="channel-uuid-1",
        order=0,
    )
    template2 = GameTemplate(
        id="template-uuid-2",
        guild_id="guild-uuid-1",
        name="Template 2",
        channel_id="channel-uuid-1",
        order=1,
    )

    async def mock_get(model, template_id):
        if template_id == "template-uuid-1":
            return template1
        elif template_id == "template-uuid-2":
            return template2
        return None

    mock_db.get.side_effect = mock_get

    template_orders = [
        {"template_id": "template-uuid-1", "order": 5},
        {"template_id": "template-uuid-2", "order": 3},
    ]

    templates = await template_service.reorder_templates(template_orders)

    assert len(templates) == 2
    assert template1.order == 5
    assert template2.order == 3
    mock_db.commit.assert_awaited_once()
    assert mock_db.refresh.await_count == 2


@pytest.mark.asyncio
async def test_reorder_templates_skips_invalid_items(template_service, mock_db):
    """Test that reorder_templates skips invalid items."""
    template1 = GameTemplate(
        id="template-uuid-1",
        guild_id="guild-uuid-1",
        name="Template 1",
        channel_id="channel-uuid-1",
        order=0,
    )

    mock_db.get.return_value = template1

    template_orders = [
        {"template_id": "template-uuid-1", "order": 5},
        {"template_id": None, "order": 3},
        {"template_id": "template-uuid-2"},
    ]

    templates = await template_service.reorder_templates(template_orders)

    assert len(templates) == 1
    assert template1.order == 5
