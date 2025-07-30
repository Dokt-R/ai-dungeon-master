import discord
from discord.ext import commands
import httpx
from packages.shared.error_handler import (
    handle_error,
    ValidationError,
    NotFoundError,
)  # noqa: F401


class AdminCog(commands.Cog):
    """Admin commands for server setup and API key management."""

    def __init__(self, bot):
        self.bot = bot
        self.api_base_url = "http://localhost:8000"  # Adjust if backend runs elsewhere

    @discord.app_commands.command(
        name="server-setup",
        description="Explain the shared API key model and submission process",
    )
    async def server_setup(self, interaction: discord.Interaction):
        try:
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
        except ValidationError as ve:
            try:
                handle_error(ve, context="discord")
            except Exception:
                pass
            await interaction.response.send_message(str(ve), ephemeral=True)
        except Exception as e:
            try:
                handle_error(e, context="discord")
            except Exception:
                pass
            await interaction.response.send_message(
                "An unexpected error occurred. Please contact an administrator.",
                ephemeral=True,
            )

    @discord.app_commands.command(
        name="server-setkey", description="Set the server's shared API key"
    )
    async def server_setkey(self, interaction: discord.Interaction, api_key: str):
        try:
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
                "player_roll_mode": "public",
                "character_sheet_mode": "digital_sheet",
            }
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.put(url, json=payload, timeout=10)
                    if response.status_code == 200:
                        await interaction.response.send_message(
                            "API key securely stored for this server.", ephemeral=True
                        )
                    else:
                        raise ValidationError(
                            f"Failed to store API key: {response.text}"
                        )
                except ValidationError as ve:
                    handle_error(ve, context="discord")
                    await interaction.response.send_message(str(ve), ephemeral=True)
                except Exception as e:
                    handle_error(e, context="discord")
                    await interaction.response.send_message(
                        "Failed to store API key. An unexpected error occurred. Please contact an administrator.",
                        ephemeral=True,
                    )
        except ValidationError as ve:
            handle_error(ve, context="discord")
            await interaction.response.send_message(str(ve), ephemeral=True)
        except Exception as e:
            handle_error(e, context="discord")
            await interaction.response.send_message(
                "An unexpected error occurred. Please contact an administrator.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
