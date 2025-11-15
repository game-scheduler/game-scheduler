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


"""Discord slash commands for game scheduling bot."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.bot.bot import GameSchedulerBot


async def setup_commands(bot: "GameSchedulerBot") -> None:
    """
    Register all slash commands with the bot.

    Args:
        bot: Bot instance to register commands with
    """
    from services.bot.commands import (
        config_channel,
        config_guild,
        list_games,
        my_games,
    )

    await list_games.setup(bot)
    await my_games.setup(bot)
    await config_guild.setup(bot)
    await config_channel.setup(bot)


__all__ = ["setup_commands"]
