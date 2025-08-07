import discord
from discord import app_commands
from discord.ext import commands
import os
import httpx

from packages.shared.error_handler import (
    discord_error_handler,
    ValidationError,
    NotFoundError,
)


class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_base_url = os.getenv("FAST_API", "http://localhost:8000")

    character = app_commands.Group(
        name="character", description="Manage your characters"
    )

    @character.command(name="add", description="Add a new character to your account.")
    @app_commands.describe(
        name="The name of your character",
        character_url="Optional: D&D Beyond character sheet URL",
    )
    @discord_error_handler()
    async def add(
        self, interaction: discord.Interaction, name: str, character_url: str = None
    ):
        """Add a new character for the user."""
        payload = {
            "player_id": str(interaction.user.id),
            "name": name,
            "character_url": character_url,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/characters/add",
                json=payload,
            )
            if response.status_code == 200:
                data = await response.json()
                await interaction.response.send_message(
                    f"Character '{name}' added successfully! (ID: {data.get('character_id')})",
                    ephemeral=True,
                )
            else:
                data = await response.json()
                raise ValidationError(
                    f"Failed to add character: {data.get('detail', response.text)}"
                )

    @character.command(name="update", description="Update an existing character.")
    @app_commands.describe(
        character_id="The ID of the character to update",
        name="New name for the character (optional)",
        character_url="New D&D Beyond URL (optional)",
    )
    @discord_error_handler()
    async def update(
        self,
        interaction: discord.Interaction,
        character_id: int,
        name: str = None,
        character_url: str = None,
    ):
        """Update character data."""
        if name is None and character_url is None:
            raise ValidationError(
                "You must provide at least one field to update (name or character_url)."
            )
        payload = {
            "character_id": character_id,
            "name": name,
            "character_url": character_url,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/characters/update",
                json=payload,
            )
            if response.status_code == 200:
                await interaction.response.send_message(
                    f"Character updated successfully.",
                    ephemeral=True,
                )
            else:
                data = await response.json()
                raise ValidationError(
                    f"Failed to update character: {data.get('detail', response.text)}"
                )

    @character.command(
        name="remove", description="Remove a character from your account."
    )
    @app_commands.describe(character_id="The ID of the character to remove")
    @discord_error_handler()
    async def remove(self, interaction: discord.Interaction, character_id: int):
        """Remove a character."""
        payload = {
            "character_id": character_id,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/characters/remove",
                json=payload,
            )
            if response.status_code == 200:
                await interaction.response.send_message(
                    f"Character removed successfully.",
                    ephemeral=True,
                )
            else:
                data = await response.json()
                raise NotFoundError(
                    f"Failed to remove character: {data.get('detail', response.text)}"
                )

    @character.command(name="list", description="List all your characters.")
    @discord_error_handler()
    async def list(self, interaction: discord.Interaction):
        """List all characters for the user."""
        payload = {
            "player_id": str(interaction.user.id),
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/characters/list",
                json=payload,
            )
            if response.status_code == 200:
                data = await response.json()
                characters = data.get("characters", [])
                if not characters:
                    await interaction.response.send_message(
                        "You have no characters.",
                        ephemeral=True,
                    )
                    return
                msg = "**Your Characters:**\n"
                for char in characters:
                    msg += f"- ID: {char['character_id']}, Name: {char['name']}, D&D Beyond: {char.get('character_url', 'N/A')}\n"
                await interaction.response.send_message(
                    msg,
                    ephemeral=True,
                )
            else:
                data = await response.json()
                raise ValidationError(
                    f"Failed to list characters: {data.get('detail', response.text)}"
                )

    async def cog_load(self):
        pass  # No-op, registration handled in __init__


async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
