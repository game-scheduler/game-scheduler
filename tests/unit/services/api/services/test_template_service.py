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

    mock_role_service = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = True

    templates = await template_service.get_templates_for_user(
        guild_id="guild-uuid-1",
        user_id="user123",
        discord_guild_id="123456789",
        role_service=mock_role_service,
        access_token="access_token",
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

    mock_role_service = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = True

    templates = await template_service.get_templates_for_user(
        guild_id="guild-uuid-1",
        user_id="user123",
        discord_guild_id="123456789",
        role_service=mock_role_service,
        access_token="access_token",
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

    mock_role_service = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = False

    templates = await template_service.get_templates_for_user(
        guild_id="guild-uuid-1",
        user_id="user123",
        discord_guild_id="123456789",
        role_service=mock_role_service,
        access_token="access_token",
    )

    assert len(templates) == 0


@pytest.mark.asyncio
async def test_get_templates_for_user_is_manager_skips_filtering(template_service, mock_db):
    """Test that is_manager=True returns all templates without role filtering."""
    restricted_template = GameTemplate(
        id="template-uuid-restricted",
        guild_id="guild-uuid-1",
        name="Manager Only Template",
        channel_id="channel-uuid-1",
        order=1,
        is_default=False,
        allowed_host_role_ids=["mgr-role-id"],
    )

    mock_scalars = Mock()
    mock_scalars.all.return_value = [restricted_template]
    mock_result = Mock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    mock_role_service = AsyncMock()

    result = await template_service.get_templates_for_user(
        guild_id="guild-uuid-1",
        user_id="user123",
        discord_guild_id="123456789",
        role_service=mock_role_service,
        access_token="access_token",
        is_manager=True,
    )

    assert len(result) == 1
    assert result[0].name == "Manager Only Template"
    mock_role_service.check_game_host_permission.assert_not_called()


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

    mock_role_service = AsyncMock()
    mock_role_service.check_game_host_permission.return_value = True

    templates = await template_service.get_templates_for_user(
        guild_id="guild-uuid-1",
        user_id="user123",
        discord_guild_id="123456789",
        role_service=mock_role_service,
        access_token="access_token",
    )

    assert len(templates) == 1
    assert templates[0].name == "Public Template"


@pytest.mark.asyncio
async def test_get_template_by_id(template_service, mock_db, sample_template):
    """Test getting template by ID."""
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = sample_template
    mock_db.execute.return_value = mock_result

    template = await template_service.get_template_by_id("template-uuid-1")

    assert template.id == "template-uuid-1"
    assert template.name == "D&D Campaign"


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
    mock_db.flush.assert_awaited_once()
    mock_db.commit.assert_not_awaited()

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
    mock_db.flush.assert_awaited_once()
    mock_db.commit.assert_not_awaited()

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
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_template_accepts_explicit_none(template_service, mock_db, sample_template):
    """Test that update_template accepts explicit None values to clear fields."""
    updates = {
        "description": None,
        "max_players": 10,
    }

    await template_service.update_template(sample_template, **updates)

    assert sample_template.description is None
    assert sample_template.max_players == 10


@pytest.mark.asyncio
async def test_clear_optional_text_fields(template_service, mock_db, sample_template):
    """Test clearing description, where, and signup_instructions to null."""
    sample_template.where = "Online via Discord"
    sample_template.signup_instructions = "React to sign up"

    updates = {
        "description": None,
        "where": None,
        "signup_instructions": None,
    }

    await template_service.update_template(sample_template, **updates)

    assert sample_template.description is None
    assert sample_template.where is None
    assert sample_template.signup_instructions is None


@pytest.mark.asyncio
async def test_update_preserves_omitted_fields(template_service, mock_db, sample_template):
    """Test that omitted fields are preserved when not in updates dict."""
    original_description = sample_template.description
    original_where = sample_template.where

    updates = {
        "name": "Updated Name",
    }

    await template_service.update_template(sample_template, **updates)

    assert sample_template.name == "Updated Name"
    assert sample_template.description == original_description
    assert sample_template.where == original_where


@pytest.mark.asyncio
async def test_clear_already_null_field(template_service, mock_db, sample_template):
    """Test clearing a field that is already null."""
    sample_template.where = None

    updates = {
        "where": None,
    }

    await template_service.update_template(sample_template, **updates)

    assert sample_template.where is None


@pytest.mark.asyncio
async def test_update_to_new_value_after_null(template_service, mock_db, sample_template):
    """Test updating a null field to a new value."""
    sample_template.description = None

    updates = {
        "description": "New description",
    }

    await template_service.update_template(sample_template, **updates)

    assert sample_template.description == "New description"


@pytest.mark.asyncio
async def test_set_default(template_service, mock_db, sample_template):
    """Test setting a template as default."""
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = sample_template
    mock_db.execute.return_value = mock_result

    template = await template_service.set_default("template-uuid-1")

    assert template.is_default is True
    assert mock_db.execute.await_count == 2  # One for select, one for update
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_default_not_found(template_service, mock_db):
    """Test setting default template when template not found."""
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(ValueError, match="Template not found"):
        await template_service.set_default("nonexistent-id")


@pytest.mark.asyncio
async def test_delete_template(template_service, mock_db, sample_template):
    """Test deleting a non-default template."""
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = sample_template
    mock_db.execute.return_value = mock_result

    await template_service.delete_template("template-uuid-1")

    mock_db.delete.assert_awaited_once_with(sample_template)
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_template_not_found(template_service, mock_db):
    """Test deleting template when not found."""
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

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
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = default_template
    mock_db.execute.return_value = mock_result

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

    def mock_execute_side_effect(query):
        # Create mock result for each execute call
        mock_result = Mock()
        # Return template1 for first call, template2 for second
        if not hasattr(mock_execute_side_effect, "call_count"):
            mock_execute_side_effect.call_count = 0

        if mock_execute_side_effect.call_count == 0:
            mock_result.scalar_one_or_none.return_value = template1
        else:
            mock_result.scalar_one_or_none.return_value = template2
        mock_execute_side_effect.call_count += 1
        return mock_result

    mock_db.execute.side_effect = mock_execute_side_effect

    template_orders = [
        {"template_id": "template-uuid-1", "order": 5},
        {"template_id": "template-uuid-2", "order": 3},
    ]

    templates = await template_service.reorder_templates(template_orders)

    assert len(templates) == 2
    assert template1.order == 5
    assert template2.order == 3
    mock_db.commit.assert_not_awaited()


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

    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = template1
    mock_db.execute.return_value = mock_result

    template_orders = [
        {"template_id": "template-uuid-1", "order": 5},
        {"template_id": None, "order": 3},
        {"template_id": "template-uuid-2"},
    ]

    templates = await template_service.reorder_templates(template_orders)

    assert len(templates) == 1
    assert template1.order == 5
