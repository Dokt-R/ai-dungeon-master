import discord
from discord.ext import commands
import httpx
from dotenv import load_dotenv
from packages.shared.error_handler import (
    handle_error,
    ValidationError,
    NotFoundError,
    discord_error_handler,
)  # noqa: F401
import os


class AdminCog(commands.Cog):
    """Admin commands for server setup and API key management."""

    def __init__(self, bot):
        self.bot = bot
        self.api_base_url = os.getenv(
            "FAST_API", "http://localhost:8000"
        )  # Adjust if backend runs elsewhere

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Event listener for when a new member joins the server.
        Creates a new player in the database.
        """
        if member.bot:
            return

        player_id = str(member.id)
        username = member.name

        url = f"{self.api_base_url}/players/create"
        payload = {"player_id": player_id, "username": username}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                print(f"Error creating player for {username} ({player_id}): {e}")

    @discord.app_commands.command(
        name="server-setup",
        description="Explain the shared API key model and submission process",
    )
    @discord_error_handler()
    async def server_setup(self, interaction: discord.Interaction):
        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild):
            raise ValidationError(
                "You need Administrator or Manage Server permissions to use this command."
            )

        explanation = (
            "**Shared API Key Model**\n"
            "This server uses a shared API key for campaign participation. "
            "To set up, an admin must submit the key using `/server-setkey [API_KEY]`. "
            "The key will be securely stored and used for all members. "
            "Only users with the required permissions can submit or update the key."
        )
        await interaction.response.send_message(explanation, ephemeral=True)

    @discord.app_commands.command(
        name="server-setkey", description="Set the server's shared API key"
    )
    @discord_error_handler()
    async def server_setkey(self, interaction: discord.Interaction, api_key: str):
        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild):
            raise ValidationError(
                "You need Administrator or Manage Server permissions to use this command."
            )

        server_id = str(interaction.guild_id)
        url = f"{self.api_base_url}/servers/{server_id}/config"
        payload = {
            "api_key": api_key,
            # Default values; could be extended to accept from user
            "dm_roll_visibility": "public",
            "player_roll_mode": "digital",
            "character_sheet_mode": "digital_sheet",
        }
        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=payload, timeout=10)
            if response.status_code == 200:
                await interaction.response.send_message(
                    "API key securely stored for this server.", ephemeral=True
                )
            else:
                raise ValidationError(f"Failed to store API key: {response.text}")


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
