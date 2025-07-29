import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

from backend.server_settings_manager import ServerSettingsManager

# Load environment variables from .env file
load_dotenv()

# Create a bot instance
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True  # Enable guilds intent
intents.message_content = True  # Enables command processing
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree


@tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")


@tree.command(
    name="server-setup",
    description="Explain the shared API key model and submission process",
)
async def server_setup(interaction: discord.Interaction):
    # Check for Administrator or Manage Guild permissions
    perms = interaction.user.guild_permissions
    if not (perms.administrator or perms.manage_guild):
        await interaction.response.send_message(
            "You need Administrator or Manage Server permissions to use this command.",
            ephemeral=True,
        )
        return

    explanation = (
        "**Shared API Key Model**\n"
        "This server uses a shared API key for campaign participation. "
        "To set up, an admin must submit the key using `/server-setkey [API_KEY]`. "
        "The key will be securely stored and used for all members. "
        "Only users with the required permissions can submit or update the key."
    )
    await interaction.response.send_message(explanation, ephemeral=True)


# Instantiate the server settings manager
settings_manager = ServerSettingsManager()


@tree.command(name="server-setkey", description="Submit the server's shared API key")
async def server_setkey(interaction: discord.Interaction, api_key: str):
    # Check for Administrator or Manage Guild permissions
    perms = interaction.user.guild_permissions
    if not (perms.administrator or perms.manage_guild):
        await interaction.response.send_message(
            "You need Administrator or Manage Server permissions to use this command.",
            ephemeral=True,
        )
        return

    # Get the server (guild) ID
    server_id = str(interaction.guild_id)
    try:
        settings_manager.store_api_key(server_id, api_key)
        await interaction.response.send_message(
            "API key securely stored for this server.", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"Failed to store API key: {str(e)}", ephemeral=True
        )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await tree.sync()  # Global sync


# Run the bot with the token from environment variable
# and prevent the bot from running on import (e.g., during tests)
if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
