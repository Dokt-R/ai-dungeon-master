import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a bot instance
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True  # Enable guilds intent
intents.message_content = True  # Enables command processing
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command()
async def ping(ctx):
    await ctx.send("pong")


# Run the bot with the token from environment variable
# and prevent the bot from running on import (e.g., during tests)
if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
