import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

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
    await bot.load_extension("cogs.utility_cog")
    await bot.load_extension("cogs.admin_cog")


if __name__ == "__main__":
    import asyncio

    async def main():
        await load_cogs()
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

    asyncio.run(main())
