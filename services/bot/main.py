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


"""Discord bot entry point."""

import asyncio
import logging
import sys

from services.bot.bot import create_bot
from services.bot.config import get_config
from shared.telemetry import flush_telemetry, init_telemetry


def setup_logging(log_level: str) -> None:
    """
    Configure logging for the bot application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


async def main() -> None:
    """Main bot application entry point."""
    config = get_config()

    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    # Initialize OpenTelemetry
    init_telemetry("bot-service")

    try:
        # Check if running in test environment without Discord credentials
        if not config.discord_bot_token or not config.discord_bot_client_id:
            logger.warning(
                "Discord credentials not configured. Bot will not start (integration test mode)."
            )
            return

        logger.info("Starting Discord Game Scheduler Bot")
        logger.info(f"Environment: {config.environment}")

        try:
            bot = await create_bot(config)

            async with bot:
                await bot.start(config.discord_bot_token)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down")
        except Exception as e:
            logger.exception(f"Fatal error: {e}")
            sys.exit(1)
    finally:
        flush_telemetry()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
