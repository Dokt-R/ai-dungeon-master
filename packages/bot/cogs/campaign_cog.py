import discord
from discord import app_commands
from discord.ext import commands
import os
import httpx


class CampaignCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_base_url = os.getenv("FAST_API", "http://localhost:8000")

    campaign = app_commands.Group(name="campaign", description="Manage campaigns")

    @campaign.command(
        name="new", description="Create a new campaign and prompt for character setup."
    )
    @app_commands.describe(name="The name of the new campaign")
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
                    f"{self.api_base_url}/campaigns/",
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
    async def join(self, interaction: discord.Interaction, name: str):
        await self._handle_campaign_join(interaction, name)

    async def _handle_campaign_join(
        self, interaction: discord.Interaction, campaign_name: str
    ):
        # Call backend API to join campaign
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/campaigns/join",
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
#TODO: Continue here
    @campaign.command(
        name="end",
        description="Exit the current campaign immersive mode and enter command mode.",
    )

    async def _handle_campaign_end(self, interaction: discord.Interaction):
        # Call backend API to join campaign
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/campaigns/end",
                    json={
                        "server_id": str(interaction.guild.id),
                        "player_id": str(interaction.user.id),
                    },
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

    async def cog_load(self):
        self.bot.tree.add_command(self.campaign)


async def setup(bot):
    await bot.add_cog(CampaignCog(bot))
