import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from packages.shared.api_client import ApiClient
from packages.shared.error_handler import discord_error_handler
from packages.shared.exceptions import PermissionDeniedError


class CampaignCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_client = ApiClient(
            base_url=os.getenv("FAST_API", "http://localhost:8000")
        )

    campaign = app_commands.Group(name="campaign", description="Manage campaigns")

    @campaign.command(
        name="create",
        description="Create a new campaign and prompt for character setup.",
    )
    @app_commands.describe(name="The name of the new campaign")
    @discord_error_handler()
    async def new(self, interaction: discord.Interaction, name: str):
        await self._handle_campaign_new(interaction, name)

    async def _handle_campaign_new(
        self, interaction: discord.Interaction, campaign_name: str
    ):
        # Permission check: Only allow users with Manage Server or Administrator
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDeniedError(
                details={"message": "This command must be used in a server."}
            )

        if not (
            interaction.user.guild_permissions.administrator
            or interaction.user.guild_permissions.manage_guild
        ):
            raise PermissionDeniedError(
                details={
                    "message": "You do not have permission to create a campaign. (Requires Manage Server or Administrator role.)"
                }
            )

        # Call backend API to create campaign
        await self.api_client.create_campaign(
            {
                "server_id": str(interaction.guild.id)
                if interaction.guild
                else "unknown",
                "campaign_name": campaign_name,
                "owner_id": str(interaction.user.id),
            }
        )

        await interaction.response.send_message(
            "**Entering immersive role-playing mode. All messages from now on will be processed by the AI.**\n"
            f"Campaign '{campaign_name}' created successfully!\n"
            "Please proceed to character setup. Would you like to use a digital or physical character sheet?",
            ephemeral=False,
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
        await self.api_client.join_campaign(
            {
                "server_id": str(interaction.guild.id)
                if interaction.guild
                else "unknown",
                "campaign_name": campaign_name,
                "player_id": str(interaction.user.id),
            }
        )

        await interaction.response.send_message(
            "**Entering immersive role-playing mode. All messages from now on will be processed by the AI.**\n"
            f"You have joined campaign '{campaign_name}'!\n"
            "Please proceed to character setup. Would you like to use a digital or physical character sheet?",
            ephemeral=False,
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
        self, interaction: discord.Interaction, campaign_name: Optional[str] = None
    ):
        # Call backend API to end campaign
        payload = {
            "server_id": str(interaction.guild.id) if interaction.guild else "unknown",
            "player_id": str(interaction.user.id),
        }
        if campaign_name:
            payload["campaign_name"] = campaign_name

        await self.api_client.end_campaign(payload)

        await interaction.response.send_message(
            "**Exiting immersive mode. Progress has been saved. You are now in command mode.**\n",
            ephemeral=False,
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
        if not isinstance(interaction.user, discord.Member):
            raise PermissionDeniedError(
                details={"message": "This command must be used in a server."}
            )

        is_admin = (
            interaction.user.guild_permissions.administrator
            or interaction.user.guild_permissions.manage_guild
        )
        button_callback = self._create_delete_confirmation_callback(name, is_admin)

        view = discord.ui.View()
        confirm_button: discord.ui.Button = discord.ui.Button(
            label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm"
        )
        cancel_button: discord.ui.Button = discord.ui.Button(
            label="Cancel", style=discord.ButtonStyle.grey, custom_id="cancel"
        )

        # Create callback functions
        async def confirm_callback(interaction: discord.Interaction):
            await button_callback(interaction, "confirm")

        async def cancel_callback(interaction: discord.Interaction):
            await button_callback(interaction, "cancel")

        confirm_button.callback = confirm_callback  # type: ignore[method-assign]
        cancel_button.callback = cancel_callback  # type: ignore[method-assign]
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(
            f"Are you sure you want to delete campaign '{name}'? This action cannot be undone.",
            view=view,
            ephemeral=True,
        )

    def _create_delete_confirmation_callback(self, name: str, is_admin: bool):
        async def button_callback(interaction: discord.Interaction, custom_id: str):
            await interaction.response.defer(ephemeral=True)
            if (
                interaction.message
                and hasattr(interaction.message, "view")
                and interaction.message.view
            ):
                view = interaction.message.view
                for item in view.children:
                    item.disabled = True

            if custom_id == "confirm":
                try:
                    await self.api_client.delete_campaign(
                        {
                            "server_id": str(interaction.guild.id)
                            if interaction.guild
                            else "unknown",
                            "campaign_name": name,
                            "requester_id": str(interaction.user.id),
                            "is_admin": is_admin,
                        }
                    )
                    await interaction.followup.send(
                        f"Campaign '{name}' deleted successfully.", ephemeral=True
                    )
                except Exception as e:
                    await self._handle_delete_error(interaction, e)
            else:
                await interaction.followup.send(
                    "Campaign deletion cancelled.", ephemeral=True
                )

            if "view" in locals():
                await interaction.edit_original_response(view=view)

        return button_callback

    async def _handle_delete_error(
        self, interaction: discord.Interaction, e: Exception
    ):
        # Re-raise the exception since the API client already handles error mapping
        raise e

    @campaign.command(name="info", description="Display information about a campaign.")
    @app_commands.describe(name="The name of the campaign to get info for.")
    @discord_error_handler()
    async def info(self, interaction: discord.Interaction, name: str):
        await self._handle_campaign_info(interaction, name)

    async def _handle_campaign_info(self, interaction: discord.Interaction, name: str):
        # Fetch campaign details from the backend
        campaign_data = await self.api_client.get_campaign_details(
            str(interaction.guild.id) if interaction.guild else "unknown", name
        )

        # Fetch the list of players in the campaign
        players_data = await self.api_client.get_campaign_players(
            campaign_data["campaign_id"]
        )
        player_names = (
            [player["username"] for player in players_data]
            if players_data
            else ["No players yet."]
        )

        # Create an embed to display the campaign information
        embed = discord.Embed(
            title=f"Campaign Info: {campaign_data['campaign_name']}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Owner ID", value=campaign_data["owner_id"], inline=False)
        embed.add_field(
            name="State", value=campaign_data.get("state", "N/A"), inline=False
        )
        embed.add_field(name="Players", value=", ".join(player_names), inline=False)
        embed.add_field(
            name="Last Save",
            value=campaign_data.get("last_save", "N/A"),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_campaign_continue(self, interaction: discord.Interaction):
        # Call backend API to continue campaign
        payload = {
            "server_id": str(interaction.guild.id) if interaction.guild else "unknown",
            "player_id": str(interaction.user.id),
            "username": str(interaction.user.display_name),
        }

        data = await self.api_client.continue_campaign(payload)

        campaign_name = data.get("campaign_name", "Unknown")
        source = data.get("source", "save")
        msg = (
            "**Entering immersive role-playing mode. All messages from now on will be processed by the AI.**\n"
            f"**Resuming campaign '{campaign_name}'.**\n"
            f"Restored from {'autosave' if source == 'autosave' else 'last clean save'}.\n"
            "You are now back in immersive role-playing mode."
        )
        await interaction.response.send_message(msg, ephemeral=False)

    async def cog_unload(self):
        """Called when the cog is unloaded. Clean up resources."""
        await self.api_client.close()


async def setup(bot):
    await bot.add_cog(CampaignCog(bot))
