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


"""Template service for game template CRUD operations."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.template import GameTemplate


class TemplateService:
    """Service for managing game templates."""

    def __init__(self, db: AsyncSession):
        """
        Initialize template service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_templates_for_user(
        self,
        guild_id: str,
        user_role_ids: list[str],
        is_admin: bool = False,
    ) -> list[GameTemplate]:
        """
        Get templates user can access, sorted for dropdown.

        Templates are sorted with default first, then by order.
        Non-admin users only see templates they have access to based on
        allowed_host_role_ids.

        Args:
            guild_id: Guild UUID
            user_role_ids: User's Discord role IDs
            is_admin: Whether user is admin (bypasses role filtering)

        Returns:
            List of accessible templates
        """
        result = await self.db.execute(
            select(GameTemplate)
            .where(GameTemplate.guild_id == guild_id)
            .order_by(
                GameTemplate.is_default.desc(),
                GameTemplate.order.asc(),
            )
        )
        templates = list(result.scalars().all())

        if not is_admin:
            templates = [
                t
                for t in templates
                if not t.allowed_host_role_ids
                or any(role_id in t.allowed_host_role_ids for role_id in user_role_ids)
            ]

        return templates

    async def get_template_by_id(self, template_id: str) -> GameTemplate | None:
        """
        Get template by ID.

        Args:
            template_id: Template UUID

        Returns:
            Template or None if not found
        """
        return await self.db.get(GameTemplate, template_id)

    async def create_template(
        self,
        guild_id: str,
        channel_id: str,
        name: str,
        **fields,
    ) -> GameTemplate:
        """
        Create new template.

        Args:
            guild_id: Guild UUID
            channel_id: Channel UUID
            name: Template name
            **fields: Additional template fields

        Returns:
            Created template
        """
        template = GameTemplate(
            guild_id=guild_id,
            channel_id=channel_id,
            name=name,
            **fields,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def create_default_template(self, guild_id: str, channel_id: str) -> GameTemplate:
        """
        Create default template for guild initialization.

        Args:
            guild_id: Guild UUID
            channel_id: Channel UUID for default template

        Returns:
            Created default template
        """
        template = GameTemplate(
            guild_id=guild_id,
            name="Default",
            description="Default game template",
            is_default=True,
            channel_id=channel_id,
            order=0,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update_template(self, template: GameTemplate, **updates) -> GameTemplate:
        """
        Update template.

        Args:
            template: Existing template
            **updates: Fields to update (only non-None values are applied)

        Returns:
            Updated template
        """
        for key, value in updates.items():
            if value is not None:
                setattr(template, key, value)

        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def set_default(self, template_id: str) -> GameTemplate:
        """
        Set template as default, unsetting others in the same guild.

        Args:
            template_id: Template UUID to set as default

        Returns:
            Updated template

        Raises:
            ValueError: If template not found
        """
        template = await self.db.get(GameTemplate, template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        await self.db.execute(
            update(GameTemplate)
            .where(
                GameTemplate.guild_id == template.guild_id,
                GameTemplate.id != template_id,
            )
            .values(is_default=False)
        )

        template.is_default = True
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: str) -> None:
        """
        Delete template.

        Args:
            template_id: Template UUID to delete

        Raises:
            ValueError: If template not found or is default template
        """
        template = await self.db.get(GameTemplate, template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        if template.is_default:
            raise ValueError("Cannot delete the default template")

        await self.db.delete(template)
        await self.db.commit()

    async def reorder_templates(self, template_orders: list[dict[str, int]]) -> list[GameTemplate]:
        """
        Bulk reorder templates.

        Args:
            template_orders: List of dicts with template_id and order

        Returns:
            List of updated templates
        """
        templates = []
        for item in template_orders:
            template_id = item.get("template_id")
            order = item.get("order")

            if template_id is None or order is None:
                continue

            template = await self.db.get(GameTemplate, template_id)
            if template:
                template.order = order
                templates.append(template)

        await self.db.commit()
        for template in templates:
            await self.db.refresh(template)

        return templates
