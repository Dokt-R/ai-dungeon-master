import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="bot.log",
    filemode="a",
)


# Load environment variables from .env file
load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands globally.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


async def load_cogs():
    await bot.load_extension("packages.bot.cogs.utility_cog")
    await bot.load_extension("packages.bot.cogs.admin_cog")
    await bot.load_extension("packages.bot.cogs.campaign_cog")
    await bot.load_extension("packages.bot.cogs.character_cog")
    # Load test cog for error handler validation
    from packages.bot.cogs.utility_cog import setup_error_test

    await setup_error_test(bot)


if __name__ == "__main__":
    import asyncio

    async def main():
        await load_cogs()
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

    asyncio.run(main())
