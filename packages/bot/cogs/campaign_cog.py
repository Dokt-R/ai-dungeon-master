import discord
from discord import app_commands
from discord.ext import commands
import os
import httpx
from packages.shared.error_handler import (
    handle_error,
    ValidationError,
    NotFoundError,
    discord_error_handler,
)


class CampaignCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_base_url = os.getenv("FAST_API", "http://localhost:8000")

    campaign = app_commands.Group(name="campaign", description="Manage campaigns")

    @campaign.command(
        name="new", description="Create a new campaign and prompt for character setup."
    )
    @app_commands.describe(name="The name of the new campaign")
    @discord_error_handler()
    async def new(self, interaction: discord.Interaction, name: str):
        await self._handle_campaign_new(interaction, name)

    async def _handle_campaign_new(
        self, interaction: discord.Interaction, campaign_name: str
    ):
        # Permission check: Only allow users with Manage Server or Administrator
        if not (
            interaction.user.guild_permissions.administrator
            or interaction.user.guild_permissions.manage_guild
        ):
            await interaction.response.send_message(
                "You do not have permission to create a campaign. (Requires Manage Server or Administrator role.)",
                ephemeral=True,
            )
            return

        # Call backend API to create campaign
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/campaigns/new",
                    json={
                        "server_id": str(interaction.guild.id),
                        "campaign_name": campaign_name,
                        "owner_id": str(interaction.user.id),
                    },
                )
                if response.status_code == 200:
                    await interaction.response.send_message(
                        "**Entering immersive role-playing mode. All messages from now on will be processed by the AI.**\n"
                        f"Campaign '{campaign_name}' created successfully!\n"
                        # TODO: This is probably redundant or invalid. A player could already have a character sheet
                        # An if statement should be implemented when we have character sheets
                        "Please proceed to character setup. Would you like to use a digital or physical character sheet?",
                        ephemeral=False,
                    )
                else:
                    data = await response.json()
                    await interaction.response.send_message(
                        f"Failed to create campaign: {data.get('detail', response.text)}",
                        ephemeral=True,
                    )
            except Exception as e:
                await interaction.response.send_message(
                    f"Failed to create campaign: {e}", ephemeral=True
                )

    @campaign.command(
        name="join",
        description="Join an existing campaign and prompt for character setup.",
    )
    @app_commands.describe(name="The name of the campaign to join")
    @discord_error_handler()
    async def join(self, interaction: discord.Interaction, name: str):
        await self._handle_campaign_join(interaction, name)

    async def _handle_campaign_join(
        self, interaction: discord.Interaction, campaign_name: str
    ):
        # Call backend API to join campaign
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/players/join_campaign",
                    json={
                        "server_id": str(interaction.guild.id),
                        "campaign_name": campaign_name,
                        "player_id": str(interaction.user.id),
                    },
                )
                if response.status_code == 200:
                    await interaction.response.send_message(
                        "**Entering immersive role-playing mode. All messages from now on will be processed by the AI.**\n"
                        f"You have joined campaign '{campaign_name}'!\n"
                        # TODO: This is probably redundant or invalid. A player could already have a character sheet
                        # An if statement should be implemented when we have character sheets
                        "Please proceed to character setup. Would you like to use a digital or physical character sheet?",
                        ephemeral=False,
                    )
                else:
                    data = await response.json()
                    await interaction.response.send_message(
                        f"Failed to join campaign: {data.get('detail', response.text)}",
                        ephemeral=True,
                    )
            except Exception as e:
                await interaction.response.send_message(
                    f"Failed to join campaign: {e}", ephemeral=True
                )

    @campaign.command(
        name="continue",
        description="Resume your last active campaign from the last save or autosave.",
    )
    @discord_error_handler()
    async def continue_(self, interaction: discord.Interaction):
        await self._handle_campaign_continue(interaction)

    @campaign.command(
        name="end",
        description="Exit the current campaign immersive mode and enter command mode.",
    )
    @discord_error_handler()
    async def end(self, interaction: discord.Interaction):
        await self._handle_campaign_end(interaction)

    async def _handle_campaign_end(
        self, interaction: discord.Interaction, campaign_name: str = None
    ):
        # Call backend API to end campaign
        payload = {
            "server_id": str(interaction.guild.id),
            "player_id": str(interaction.user.id),
        }
        if campaign_name:
            payload["campaign_name"] = campaign_name
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/players/end_campaign",
                    json=payload,
                )
                if response.status_code == 200:
                    await interaction.response.send_message(
                        "**Exiting immersive mode. Progress has been saved. You are now in command mode.**\n",
                        ephemeral=False,
                    )
                else:
                    data = await response.json()
                    await interaction.response.send_message(
                        f"Failed to exit campaign: {data.get('detail', response.text)}",
                        ephemeral=True,
                    )
            except Exception as e:
                await interaction.response.send_message(
                    f"Failed to exit campaign: {e}", ephemeral=True
                )

    @campaign.command(
        name="delete", description="Delete a campaign (only owner or server admin)."
    )
    @app_commands.describe(name="The name of the campaign to delete")
    @discord_error_handler()
    async def delete(self, interaction: discord.Interaction, name: str):
        await self._handle_campaign_delete(interaction, name)

    async def _handle_campaign_delete(
        self, interaction: discord.Interaction, name: str
    ):
        # Permission check: Only allow campaign owner or server admin
        # Fetch campaign info from backend to get owner_id
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/campaigns/list",  # Not implemented, so fallback to join for now
                    json={
                        "server_id": str(interaction.guild.id),
                        "campaign_name": name,
                        "player_id": str(interaction.user.id),
                    },
                )
                # If backend had a campaign info endpoint, use it. For now, assume owner is the creator.
                # We'll check permissions after confirmation.
            except Exception as e:
                await interaction.response.send_message(
                    f"Failed to fetch campaign info: {e}", ephemeral=True
                )
                return

        # Ask for confirmation
        await interaction.response.send_message(
            f"Are you sure you want to delete campaign '{name}'? This action cannot be undone. "
            "Reply with 'yes' to confirm or 'no' to cancel.",
            ephemeral=True,
        )

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
                and m.content.lower() in ["yes", "no"]
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except Exception:
            await interaction.followup.send(
                "Timed out waiting for confirmation.", ephemeral=True
            )
            return

        if msg.content.lower() != "yes":
            await interaction.followup.send(
                "Campaign deletion cancelled.", ephemeral=True
            )
            return

        # Check permissions: owner or admin
        is_admin = (
            interaction.user.guild_permissions.administrator
            or interaction.user.guild_permissions.manage_guild
        )
        # Fetch campaign owner from backend
        owner_id = None
        async with httpx.AsyncClient() as client:
            try:
                # Use join to get error if campaign doesn't exist, else get owner_id
                response = await client.post(
                    f"{self.api_base_url}/campaigns/new",  # Not ideal, but no info endpoint
                    json={
                        "server_id": str(interaction.guild.id),
                        "campaign_name": name,
                        "owner_id": str(interaction.user.id),
                    },
                )
                # If status 400, campaign exists, get owner_id
                # This is a hack; ideally, there should be a campaign info endpoint.
                if response.status_code == 400:
                    data = await response.json()
                    detail = data.get("detail", "")
                    # Parse owner_id from error if possible (not implemented)
                    # For now, assume only admins can delete if not owner
                    if not is_admin:
                        await interaction.followup.send(
                            "You do not have permission to delete this campaign. (Only the owner or a server admin can delete.)",
                            ephemeral=True,
                        )
                        return
                # If status 200, campaign does not exist (should not happen)
                elif response.status_code == 200:
                    await interaction.followup.send(
                        f"No campaign named '{name}' exists on this server.",
                        ephemeral=True,
                    )
                    return
            except Exception as e:
                await interaction.followup.send(
                    f"Failed to check campaign permissions: {e}", ephemeral=True
                )
                return

        # Call backend to delete
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/campaigns/delete",
                    json={
                        "server_id": str(interaction.guild.id),
                        "campaign_name": name,
                        "requester_id": str(interaction.user.id),
                        "is_admin": is_admin,
                    },
                )
                if response.status_code == 200:
                    await interaction.followup.send(
                        f"Campaign '{name}' deleted successfully.",
                        ephemeral=False,
                    )
                else:
                    data = await response.json()
                    await interaction.followup.send(
                        f"Failed to delete campaign: {data.get('detail', response.text)}",
                        ephemeral=True,
                    )
            except Exception as e:
                await interaction.followup.send(
                    f"Failed to delete campaign: {e}", ephemeral=True
                )
        return

    async def _handle_campaign_continue(self, interaction: discord.Interaction):
        # Call backend API to continue campaign
        payload = {
            "server_id": str(interaction.guild.id),
            "player_id": str(interaction.user.id),
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/players/continue_campaign",
                    json=payload,
                )
                if response.status_code == 200:
                    data = response.json()
                    campaign_name = data.get("campaign_name", "Unknown")
                    source = data.get("source", "save")
                    msg = (
                        "**Entering immersive role-playing mode. All messages from now on will be processed by the AI.**\n"
                        f"**Resuming campaign '{campaign_name}'.**\n"
                        f"Restored from {'autosave' if source == 'autosave' else 'last clean save'}.\n"
                        "You are now back in immersive role-playing mode."
                    )
                    await interaction.response.send_message(msg, ephemeral=False)
                    # TODO: After all validations pass, update only the allowed sections of the story file
                    # according to the develop-story workflow. This should be implemented here or in the backend.
                else:
                    data = await response.json()
                    await interaction.response.send_message(
                        f"Failed to continue campaign: {data.get('detail', response.text)}",
                        ephemeral=True,
                    )
            except Exception as e:
                await interaction.response.send_message(
                    f"Failed to continue campaign: {e}", ephemeral=True
                )

    async def cog_load(self):
        self.bot.tree.add_command(self.campaign)


async def setup(bot):
    await bot.add_cog(CampaignCog(bot))
