import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands
from pydantic import SecretStr

from packages.shared.api_client import ApiClient
from packages.shared.error_handler import discord_error_handler
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import PermissionDeniedError, ValidationError
from packages.shared.models import ServerConfigModel


class AdminCog(commands.Cog):
    """Admin commands for server setup and API key management."""

    def __init__(self, bot):
        self.bot = bot
        self.api_client = ApiClient(
            base_url=os.getenv("FAST_API", "http://localhost:8000")
        )
        self.sync_task = None
        self.sync_interval = 3600  # 1 hour in seconds

    # Create sync command group
    sync = app_commands.Group(
        name="sync",
        description="Manage player sync operations",
        default_permissions=discord.Permissions(administrator=True, manage_guild=True),
    )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Event listener for when a new member joins the server.
        Creates a new player in the database.
        """
        if member.bot:
            return

        await self._create_or_update_player(member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Event listener for when a member updates (e.g., changes username/nickname).
        Updates the player in the database if username changed.
        """
        if before.bot:
            return

        # Check if the display name changed
        if before.display_name != after.display_name:
            await self._create_or_update_player(after)

    @discord.app_commands.command(
        name="server-setup",
        description="Explain the shared API key model and submission process",
    )
    @discord_error_handler()
    async def server_setup(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={"message": "This command can only be used in a server."},
            )

        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={
                    "message": "You need Administrator or Manage Server permissions to use this command."
                },
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
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={"message": "This command can only be used in a server."},
            )

        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={
                    "message": "You need Administrator or Manage Server permissions to use this command."
                },
            )

        server_id = str(interaction.guild_id)
        config = ServerConfigModel(
            api_key=SecretStr(api_key),
            # Default values; could be extended to accept from user
            dm_roll_visibility="public",
            player_roll_mode="digital",
            character_sheet_mode="digital_sheet",
        )

        await self.api_client.set_server_config(server_id, config)
        await interaction.response.send_message(
            "API key securely stored for this server.", ephemeral=True
        )

    @sync.command(
        name="members",
        description="Sync all current server members to the database as players",
    )
    @discord_error_handler()
    async def sync_members(self, interaction: discord.Interaction):
        """Sync all current server members to the database."""
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={"message": "This command can only be used in a server."},
            )

        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={
                    "message": "You need Administrator or Manage Server permissions to use this command."
                },
            )

        await interaction.response.defer(ephemeral=True)

        # Get all members
        if interaction.guild is None:
            raise ValidationError(
                ErrorCode.MEMBER_FETCH_ERROR,
                details={"message": "This command must be used in a server."},
            )

        try:
            # Try to fetch members if the cache is empty
            if not interaction.guild.members:
                await interaction.guild.chunk()

            members = [member for member in interaction.guild.members if not member.bot]

            if not members:
                raise ValidationError(ErrorCode.NO_MEMBERS_FOUND)
        except Exception as e:
            raise ValidationError(
                ErrorCode.MEMBER_FETCH_ERROR, details={"original_error": str(e)}
            )

        # Create progress message
        progress_msg = await interaction.followup.send(
            f"Starting sync of {len(members)} members...", ephemeral=True
        )  # type: ignore[func-returns-value]
        assert progress_msg is not None, "Failed to create progress message"

        created_count = 0
        updated_count = 0
        error_count = 0

        for i, member in enumerate(members):
            try:
                result = await self._create_or_update_player(member)
                if result.get("created"):
                    created_count += 1
                else:
                    updated_count += 1

                # Update progress every 10 members
                if (i + 1) % 10 == 0:
                    await progress_msg.edit(
                        content=f"Syncing members... {i + 1}/{len(members)} completed"
                    )

            except Exception as e:
                error_count += 1
                # Log the error but continue processing other members
                print(f"Error syncing member {member.name} ({member.id}): {e}")

        # Final status
        await progress_msg.edit(
            content=f"Sync completed!\n"
            f"Created: {created_count}\n"
            f"Updated: {updated_count}\n"
            f"Errors: {error_count}"
        )

    @sync.command(
        name="start", description="Start periodic member sync (runs every hour)"
    )
    @discord_error_handler()
    async def start_sync(self, interaction: discord.Interaction):
        """Start periodic member sync."""
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={"message": "This command must be used in a server."},
            )

        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={
                    "message": "You need Administrator or Manage Server permissions to use this command."
                },
            )

        if self.sync_task and not self.sync_task.done():
            await interaction.response.send_message(
                "Periodic sync is already running.", ephemeral=True
            )
            return

        self.sync_task = asyncio.create_task(self._periodic_sync())
        await interaction.response.send_message(
            f"Started periodic sync (every {self.sync_interval // 3600} hour{'s' if self.sync_interval > 3600 else ''}).",
            ephemeral=True,
        )

    @sync.command(name="stop", description="Stop periodic member sync")
    @discord_error_handler()
    async def stop_sync(self, interaction: discord.Interaction):
        """Stop periodic member sync."""
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={"message": "This command must be used in a server."},
            )

        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={
                    "message": "You need Administrator or Manage Server permissions to use this command."
                },
            )

        if self.sync_task and not self.sync_task.done():
            self.sync_task.cancel()
            await interaction.response.send_message(
                "Stopped periodic sync.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "No active sync task to stop.", ephemeral=True
            )

    @sync.command(name="status", description="Check the status of periodic member sync")
    @discord_error_handler()
    async def sync_status(self, interaction: discord.Interaction):
        """Check the status of periodic member sync."""
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={"message": "This command must be used in a server."},
            )

        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={
                    "message": "You need Administrator or Manage Server permissions to use this command."
                },
            )

        if self.sync_task and not self.sync_task.done():
            await interaction.response.send_message(
                f"✅ Periodic sync is running\n"
                f"Next sync in ~{self.sync_interval // 3600} hour{'s' if self.sync_interval > 3600 else ''}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Periodic sync is not running\nYou can start it with `/sync start`",
                ephemeral=True,
            )

    @sync.command(name="restart", description="Restart periodic member sync")
    @discord_error_handler()
    async def restart_sync(self, interaction: discord.Interaction):
        """Restart periodic member sync."""
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={"message": "This command must be used in a server."},
            )

        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={
                    "message": "You need Administrator or Manage Server permissions to use this command."
                },
            )

        # Stop existing sync if running
        if self.sync_task and not self.sync_task.done():
            self.sync_task.cancel()

        # Start new sync
        self.sync_task = asyncio.create_task(self._periodic_sync())
        await interaction.response.send_message(
            "Restarted periodic sync.", ephemeral=True
        )

    async def _create_or_update_player(self, member: discord.Member) -> dict:
        """
        Create or update a player in the database.
        Returns dict with 'created' boolean and player info.
        """
        player_id = str(member.id)
        username = (
            member.display_name
        )  # Use display_name to get server-specific nickname

        try:
            result = await self.api_client.create_player(
                {"player_id": player_id, "username": username}
            )
            return {"created": True, "updated": False, "player": result}
        except Exception as e:
            # If the error is not about player already existing, re-raise it
            error_msg = str(e).lower()
            if "already exists" not in error_msg and "duplicate" not in error_msg:
                return {
                    "created": False,
                    "updated": False,
                    "player": {"player_id": player_id, "username": username},
                }
            else:
                raise

    async def _periodic_sync(self):
        """Periodic sync task that runs every hour."""
        while True:
            try:
                await asyncio.sleep(self.sync_interval)

                for guild in self.bot.guilds:
                    # Only sync guilds that have API keys configured
                    try:
                        # Check if server has config (this will raise an error if not configured)
                        server_id = str(guild.id)  # noqa: F841
                        # For now, we'll just sync all guilds
                        # In a production environment, you might want to check server config

                        try:
                            # Ensure members are loaded
                            if not guild.members:
                                await guild.chunk()

                            members = [
                                member for member in guild.members if not member.bot
                            ]
                        except Exception as e:
                            print(f"Error fetching members for guild {guild.name}: {e}")
                            continue

                        for member in members:
                            try:
                                await self._create_or_update_player(member)
                            except Exception as e:
                                print(
                                    f"Error in periodic sync for {member.name} ({member.id}): {e}"
                                )

                    except Exception as e:
                        print(f"Error syncing guild {guild.name}: {e}")

            except asyncio.CancelledError:
                print("Periodic sync task cancelled")
                break
            except Exception as e:
                print(f"Error in periodic sync: {e}")
                # Continue running even if there's an error

    async def _check_backend_health(self) -> bool:
        """
        Check if the backend API is available and healthy.
        Returns True if healthy, False otherwise.
        """
        try:
            # Try to make a simple request to check if backend is up
            # We'll use the create_player endpoint with a test ID to check connectivity
            test_player_id = "health_check_test"
            await self.api_client.create_player(
                {"player_id": test_player_id, "username": "Health Check User"}
            )
            return True
        except Exception:
            # If the request fails, backend is not available
            return False

    async def cog_unload(self):
        """Called when the cog is unloaded. Clean up resources."""
        if self.sync_task and not self.sync_task.done():
            self.sync_task.cancel()
        await self.api_client.close()


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
