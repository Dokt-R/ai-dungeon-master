import os

import discord
import httpx
from discord import app_commands
from discord.ext import commands

from packages.shared.error_handler import (
    NotFoundError,
    ValidationError,
    discord_error_handler,
)


class CampaignCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_base_url = os.getenv("FAST_API", "http://localhost:8000")

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
                    f"{self.api_base_url}/campaigns/create",
                    json={
                        "server_id": str(interaction.guild.id),
                        "campaign_name": campaign_name,
                        "owner_id": str(interaction.user.id),
                    },
                )
                response.raise_for_status()

                data = await response.json()

                await interaction.response.send_message(
                    "**Entering immersive role-playing mode. All messages from now on will be processed by the AI.**\n"
                    f"Campaign '{campaign_name}' created successfully!\n"
                    "Please proceed to character setup. Would you like to use a digital or physical character sheet?",
                    ephemeral=False,
                )
            except httpx.HTTPStatusError as e:
                message = "Failed to create campaign. Please try again later."
                if e.response:
                    try:
                        data = await e.response.json()
                        message = data.get("error", {}).get("message", message)
                    except (ValueError, httpx.HTTPError):
                        pass
                raise ValidationError(message)
            except Exception:
                raise ValidationError(
                    "An unexpected error occurred while creating the campaign. Please try again later."
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
                response.raise_for_status()
                await interaction.response.send_message(
                    "**Entering immersive role-playing mode. All messages from now on will be processed by the AI.**\n"
                    f"You have joined campaign '{campaign_name}'!\n"
                    "Please proceed to character setup. Would you like to use a digital or physical character sheet?",
                    ephemeral=False,
                )
            except httpx.HTTPStatusError as e:
                message = "Failed to join campaign. Please try again later."
                if e.response:
                    try:
                        data = await e.response.json()
                        message = data.get("error", {}).get("message", message)
                    except ValueError:
                        pass
                if e.response and e.response.status_code == 404:
                    raise NotFoundError(message)
                raise ValidationError(message)
            except Exception:
                raise ValidationError(
                    "An unexpected error occurred while joining the campaign. Please try again later."
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
                response.raise_for_status()
                await interaction.response.send_message(
                    "**Exiting immersive mode. Progress has been saved. You are now in command mode.**\n",
                    ephemeral=False,
                )
            except httpx.HTTPStatusError as e:
                message = "Failed to exit campaign. Please try again later."
                if e.response:
                    try:
                        data = await e.response.json()
                        message = data.get("error", {}).get("message", message)
                    except ValueError:
                        pass
                raise ValidationError(message)
            except Exception:
                raise ValidationError(
                    "An unexpected error occurred while exiting the campaign. Please try again later."
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
        is_admin = (
            interaction.user.guild_permissions.administrator
            or interaction.user.guild_permissions.manage_guild
        )
        button_callback = self._create_delete_confirmation_callback(name, is_admin)

        view = discord.ui.View()
        confirm_button = discord.ui.Button(
            label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm"
        )
        cancel_button = discord.ui.Button(
            label="Cancel", style=discord.ButtonStyle.grey, custom_id="cancel"
        )
        confirm_button.callback = button_callback
        cancel_button.callback = button_callback
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(
            f"Are you sure you want to delete campaign '{name}'? This action cannot be undone.",
            view=view,
            ephemeral=True,
        )

    def _create_delete_confirmation_callback(self, name: str, is_admin: bool):
        async def button_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            view = interaction.message.view
            for item in view.children:
                item.disabled = True

            if interaction.data["custom_id"] == "confirm":
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.request(
                            "DELETE",
                            f"{self.api_base_url}/campaigns/delete",
                            json={
                                "server_id": str(interaction.guild.id),
                                "campaign_name": name,
                                "requester_id": str(interaction.user.id),
                                "is_admin": is_admin,
                            },
                        )
                        response.raise_for_status()
                        await interaction.followup.send(
                            f"Campaign '{name}' deleted successfully.", ephemeral=True
                        )
                except Exception as e:
                    await self._handle_delete_error(interaction, e)
            else:
                await interaction.followup.send(
                    "Campaign deletion cancelled.", ephemeral=True
                )

            await interaction.edit_original_response(view=view)

        return button_callback

    async def _handle_delete_error(
        self, interaction: discord.Interaction, e: Exception
    ):
        if isinstance(e, httpx.HTTPStatusError):
            message = "Failed to delete campaign. Please try again later."
            if e.response:
                try:
                    data = await e.response.json()
                    message = data.get("error", {}).get("message", message)
                except ValueError:
                    pass
            raise ValidationError(message)
        else:
            raise ValidationError(
                "An unexpected error occurred while deleting the campaign. Please try again later."
            )

    @campaign.command(name="info", description="Display information about a campaign.")
    @app_commands.describe(name="The name of the campaign to get info for.")
    @discord_error_handler()
    async def info(self, interaction: discord.Interaction, name: str):
        await self._handle_campaign_info(interaction, name)

    async def _handle_campaign_info(self, interaction: discord.Interaction, name: str):
        try:
            async with httpx.AsyncClient() as client:
                # Fetch campaign details from the backend.
                response = await client.get(
                    f"{self.api_base_url}/campaigns/{interaction.guild.id}/{name}"
                )
                response.raise_for_status()
                campaign_data = response.json()

                # Fetch the list of players in the campaign.
                players_response = await client.get(
                    f"{self.api_base_url}/campaigns/{campaign_data['campaign_id']}/players"
                )
                players_response.raise_for_status()
                players_data = players_response.json()
                player_names = (
                    [player["username"] for player in players_data]
                    if players_data
                    else ["No players yet."]
                )

                # Create an embed to display the campaign information.
                embed = discord.Embed(
                    title=f"Campaign Info: {campaign_data['campaign_name']}",
                    color=discord.Color.blue(),
                )
                embed.add_field(
                    name="Owner ID", value=campaign_data["owner_id"], inline=False
                )
                embed.add_field(
                    name="State", value=campaign_data.get("state", "N/A"), inline=False
                )
                embed.add_field(
                    name="Players", value=", ".join(player_names), inline=False
                )
                embed.add_field(
                    name="Last Save",
                    value=campaign_data.get("last_save", "N/A"),
                    inline=False,
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except httpx.HTTPStatusError as e:
            if e.response and e.response.status_code == 404:
                await interaction.response.send_message(
                    "Campaign not found.", ephemeral=True
                )
            else:
                message = "Failed to get campaign information. Please try again later."
                if e.response:
                    try:
                        data = await e.response.json()
                        message = data.get("error", {}).get("message", message)
                    except ValueError:
                        pass
                raise ValidationError(message)
        except Exception:
            raise ValidationError(
                "An unexpected error occurred while getting campaign information. Please try again later."
            )

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
                response.raise_for_status()
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
            except httpx.HTTPStatusError as e:
                message = "Failed to continue campaign. Please try again later."
                if e.response:
                    try:
                        data = await e.response.json()
                        message = data.get("error", {}).get("message", message)
                    except ValueError:
                        pass
                raise ValidationError(message)
            except Exception:
                raise ValidationError(
                    "An unexpected error occurred while continuing the campaign. Please try again later."
                )


async def setup(bot):
    await bot.add_cog(CampaignCog(bot))
