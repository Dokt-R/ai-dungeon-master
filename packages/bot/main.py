import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from packages.shared.correlation import (
    correlation_id_context,
)
from packages.shared.logging_config import configure_logging, get_logger

load_dotenv()
# configure_logging(log_to_file=False, path="logs/bot.log")
configure_logging()

# Create logger instance
logger = get_logger(__name__)

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    with correlation_id_context():
        logger.info("Bot logged in", bot_user=str(bot.user))
        try:
            synced = (
                await bot.tree.sync()
            )  # For production global sync, commands take up to 1 hour to sync
            logger.info("Commands synced", count=len(synced))
        except Exception as e:
            logger.error("Command sync failed", error=str(e))

        # Auto-start periodic member sync with a delay to ensure everything is loaded
        async def delayed_sync_start():
            await asyncio.sleep(5)  # Wait 5 seconds for everything to load
            try:
                admin_cog = bot.get_cog("AdminCog")
                if admin_cog:
                    logger.info("AdminCog found, attempting to start sync")

                    # Check if backend is available before starting sync
                    try:
                        health_check = await admin_cog._check_backend_health()
                        logger.info(f"Backend health check result: {health_check}")
                        if health_check:
                            # Do initial sync of all current members
                            logger.info("Starting initial member sync...")
                            for guild in bot.guilds:
                                try:
                                    await guild.chunk()  # Ensure members are loaded
                                    members = [
                                        member
                                        for member in guild.members
                                        if not member.bot
                                    ]
                                    logger.info(
                                        f"Syncing {len(members)} members from {guild.name}"
                                    )
                                    for member in members:
                                        try:
                                            await admin_cog._create_or_update_player(
                                                member
                                            )
                                        except Exception as e:
                                            logger.error(
                                                f"Error syncing member {member.name}: {e}"
                                            )
                                except Exception as e:
                                    logger.error(
                                        f"Error syncing guild {guild.name}: {e}"
                                    )

                            # Start periodic sync
                            admin_cog.sync_task = asyncio.create_task(
                                admin_cog._periodic_sync()
                            )
                            logger.info("Started automatic periodic member sync")
                        else:
                            logger.warning("Backend not available, skipping sync start")
                    except Exception as health_error:
                        logger.error(f"Health check failed: {health_error}")
                        # Try to start periodic sync anyway, it will handle errors gracefully
                        admin_cog.sync_task = asyncio.create_task(
                            admin_cog._periodic_sync()
                        )
                        logger.info(
                            "Started periodic sync despite health check failure"
                        )
                else:
                    logger.warning("AdminCog not found, cannot start sync")
            except Exception as e:
                logger.error("Failed to start sync", error=str(e))

        # Start the delayed sync task
        asyncio.create_task(delayed_sync_start())


async def load_cogs():
    await bot.load_extension("packages.bot.cogs.utility_cog")
    await bot.load_extension("packages.bot.cogs.admin_cog")
    await bot.load_extension("packages.bot.cogs.campaign_cog")
    await bot.load_extension("packages.bot.cogs.character_cog")
    await bot.load_extension("packages.bot.cogs.voice_cog")
    await bot.load_extension("packages.bot.cogs.health_cog")
    # Load test cog for error handler validation
    from packages.bot.cogs.utility_cog import setup_error_test

    await setup_error_test(bot)


if __name__ == "__main__":

    async def main():
        await load_cogs()
        token = os.getenv("DISCORD_BOT_TOKEN")

        if not token:
            logger.error("DISCORD_BOT_TOKEN missing in environment; aborting startup")
            return

        try:
            await bot.start(token)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Received keyboard interrupt, closing bot")
            await bot.close()
        except Exception:
            logger.exception("Bot crashed unexpectedly")
            await bot.close()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Force exit")
