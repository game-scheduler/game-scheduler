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


"""Game template endpoints."""

# ruff: noqa: B008
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api import dependencies
from services.api.auth import discord_client as discord_client_module
from services.api.auth import roles as roles_module
from services.api.database import queries
from services.api.services import template_service as template_service_module
from shared import database
from shared.schemas import auth as auth_schemas
from shared.schemas import template as template_schemas
from shared.utils.discord import DiscordPermissions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["templates"])


@router.get("/guilds/{guild_id}/templates", response_model=list[template_schemas.TemplateListItem])
async def list_templates(
    guild_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> list[template_schemas.TemplateListItem]:
    """
    List templates for a guild with role-based filtering.

    Templates are filtered by allowed_host_role_ids unless user is guild admin.
    Sorted with default template first, then by order.
    """
    guild_config = await queries.get_guild_by_id(db, guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    # Check if user has MANAGE_GUILD permission
    role_service = roles_module.get_role_service()
    is_admin = await role_service.has_permissions(
        current_user.user.discord_id,
        guild_config.guild_id,
        current_user.access_token,
        DiscordPermissions.MANAGE_GUILD,
    )

    # Get user's role IDs for filtering
    discord_client = discord_client_module.get_discord_client()
    member = await discord_client.get_guild_member(
        guild_config.guild_id, current_user.user.discord_id
    )
    user_role_ids = member.get("roles", [])

    # Get templates
    template_svc = template_service_module.TemplateService(db)
    templates = await template_svc.get_templates_for_user(guild_id, user_role_ids, is_admin)

    # Convert to response format with channel names
    result = []
    for template in templates:
        channel_name = await discord_client_module.fetch_channel_name_safe(
            template.channel.channel_id
        )
        result.append(
            template_schemas.TemplateListItem(
                id=template.id,
                name=template.name,
                description=template.description,
                is_default=template.is_default,
                channel_id=template.channel_id,
                channel_name=channel_name,
                notify_role_ids=template.notify_role_ids,
                allowed_player_role_ids=template.allowed_player_role_ids,
                allowed_host_role_ids=template.allowed_host_role_ids,
                max_players=template.max_players,
                expected_duration_minutes=template.expected_duration_minutes,
                reminder_minutes=template.reminder_minutes,
                where=template.where,
                signup_instructions=template.signup_instructions,
            )
        )

    return result


@router.get("/templates/{template_id}", response_model=template_schemas.TemplateResponse)
async def get_template(
    template_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> template_schemas.TemplateResponse:
    """Get template details by ID."""
    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Resolve channel name
    channel_name = await discord_client_module.fetch_channel_name_safe(template.channel.channel_id)

    return template_schemas.TemplateResponse(
        id=template.id,
        guild_id=template.guild_id,
        name=template.name,
        description=template.description,
        order=template.order,
        is_default=template.is_default,
        channel_id=template.channel_id,
        channel_name=channel_name,
        notify_role_ids=template.notify_role_ids,
        allowed_player_role_ids=template.allowed_player_role_ids,
        allowed_host_role_ids=template.allowed_host_role_ids,
        max_players=template.max_players,
        expected_duration_minutes=template.expected_duration_minutes,
        reminder_minutes=template.reminder_minutes,
        where=template.where,
        signup_instructions=template.signup_instructions,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.post(
    "/guilds/{guild_id}/templates",
    response_model=template_schemas.TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    guild_id: str,
    request: template_schemas.TemplateCreateRequest,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> template_schemas.TemplateResponse:
    """Create new template (requires bot manager role)."""
    guild_config = await queries.get_guild_by_id(db, guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    # Check bot manager permission
    role_service = roles_module.get_role_service()
    has_permission = await role_service.check_bot_manager_permission(
        current_user.user.discord_id, guild_config.guild_id, db, current_user.access_token
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot manager role required to create templates",
        )

    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.create_template(
        guild_id=guild_id,
        channel_id=request.channel_id,
        name=request.name,
        description=request.description,
        order=request.order,
        is_default=request.is_default,
        notify_role_ids=request.notify_role_ids,
        allowed_player_role_ids=request.allowed_player_role_ids,
        allowed_host_role_ids=request.allowed_host_role_ids,
        max_players=request.max_players,
        expected_duration_minutes=request.expected_duration_minutes,
        reminder_minutes=request.reminder_minutes,
        where=request.where,
        signup_instructions=request.signup_instructions,
    )

    # Resolve channel name
    channel_name = await discord_client_module.fetch_channel_name_safe(template.channel.channel_id)

    return template_schemas.TemplateResponse(
        id=template.id,
        guild_id=template.guild_id,
        name=template.name,
        description=template.description,
        order=template.order,
        is_default=template.is_default,
        channel_id=template.channel_id,
        channel_name=channel_name,
        notify_role_ids=template.notify_role_ids,
        allowed_player_role_ids=template.allowed_player_role_ids,
        allowed_host_role_ids=template.allowed_host_role_ids,
        max_players=template.max_players,
        expected_duration_minutes=template.expected_duration_minutes,
        reminder_minutes=template.reminder_minutes,
        where=template.where,
        signup_instructions=template.signup_instructions,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.put("/templates/{template_id}", response_model=template_schemas.TemplateResponse)
async def update_template(
    template_id: str,
    request: template_schemas.TemplateUpdateRequest,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> template_schemas.TemplateResponse:
    """Update template (requires bot manager role)."""
    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    guild_config = await queries.get_guild_by_id(db, template.guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    # Check bot manager permission
    role_service = roles_module.get_role_service()
    has_permission = await role_service.check_bot_manager_permission(
        current_user.user.discord_id, guild_config.guild_id, db, current_user.access_token
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot manager role required to update templates",
        )

    # Update template
    updated_template = await template_svc.update_template(
        template,
        **request.model_dump(exclude_unset=True),
    )

    # Resolve channel name
    channel_name = await discord_client_module.fetch_channel_name_safe(
        updated_template.channel.channel_id
    )

    return template_schemas.TemplateResponse(
        id=updated_template.id,
        guild_id=updated_template.guild_id,
        name=updated_template.name,
        description=updated_template.description,
        order=updated_template.order,
        is_default=updated_template.is_default,
        channel_id=updated_template.channel_id,
        channel_name=channel_name,
        notify_role_ids=updated_template.notify_role_ids,
        allowed_player_role_ids=updated_template.allowed_player_role_ids,
        allowed_host_role_ids=updated_template.allowed_host_role_ids,
        max_players=updated_template.max_players,
        expected_duration_minutes=updated_template.expected_duration_minutes,
        reminder_minutes=updated_template.reminder_minutes,
        where=updated_template.where,
        signup_instructions=updated_template.signup_instructions,
        created_at=updated_template.created_at.isoformat(),
        updated_at=updated_template.updated_at.isoformat(),
    )


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> None:
    """Delete template (requires bot manager role, cannot delete is_default)."""
    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    guild_config = await queries.get_guild_by_id(db, template.guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    # Check bot manager permission
    role_service = roles_module.get_role_service()
    has_permission = await role_service.check_bot_manager_permission(
        current_user.user.discord_id, guild_config.guild_id, db, current_user.access_token
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot manager role required to delete templates",
        )

    # Prevent deleting default template
    if template.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default template",
        )

    await template_svc.delete_template(template_id)


@router.post(
    "/templates/{template_id}/set-default", response_model=template_schemas.TemplateResponse
)
async def set_default_template(
    template_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> template_schemas.TemplateResponse:
    """Set template as default (requires bot manager role)."""
    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    guild_config = await queries.get_guild_by_id(db, template.guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    # Check bot manager permission
    role_service = roles_module.get_role_service()
    has_permission = await role_service.check_bot_manager_permission(
        current_user.user.discord_id, guild_config.guild_id, db, current_user.access_token
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot manager role required to set default template",
        )

    updated_template = await template_svc.set_default(template_id)

    # Resolve channel name
    channel_name = await discord_client_module.fetch_channel_name_safe(
        updated_template.channel.channel_id
    )

    return template_schemas.TemplateResponse(
        id=updated_template.id,
        guild_id=updated_template.guild_id,
        name=updated_template.name,
        description=updated_template.description,
        order=updated_template.order,
        is_default=updated_template.is_default,
        channel_id=updated_template.channel_id,
        channel_name=channel_name,
        notify_role_ids=updated_template.notify_role_ids,
        allowed_player_role_ids=updated_template.allowed_player_role_ids,
        allowed_host_role_ids=updated_template.allowed_host_role_ids,
        max_players=updated_template.max_players,
        expected_duration_minutes=updated_template.expected_duration_minutes,
        reminder_minutes=updated_template.reminder_minutes,
        where=updated_template.where,
        signup_instructions=updated_template.signup_instructions,
        created_at=updated_template.created_at.isoformat(),
        updated_at=updated_template.updated_at.isoformat(),
    )


@router.post("/templates/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_templates(
    request: template_schemas.TemplateReorderRequest,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> None:
    """Bulk reorder templates (requires bot manager role)."""
    if not request.template_orders:
        return

    # Extract template IDs from template_orders
    template_ids = [list(item.keys())[0] for item in request.template_orders]

    # Get first template to check guild and permissions
    template_svc = template_service_module.TemplateService(db)
    first_template = await template_svc.get_template_by_id(template_ids[0])

    if not first_template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    guild_config = await queries.get_guild_by_id(db, first_template.guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found"
        )

    # Check bot manager permission
    role_service = roles_module.get_role_service()
    has_permission = await role_service.check_bot_manager_permission(
        current_user.user.discord_id, guild_config.guild_id, db, current_user.access_token
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot manager role required to reorder templates",
        )

    await template_svc.reorder_templates(request.template_orders)
