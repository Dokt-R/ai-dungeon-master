import os

import discord
from discord import app_commands
from discord.ext import commands

from packages.shared.api_client import ApiClient
from packages.shared.error_handler import discord_error_handler
from packages.shared.models import (
    AddCharacterRequest,
    ListCharactersRequest,
    RemoveCharacterRequest,
    UpdateCharacterRequest,
)


class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_client = ApiClient(base_url=os.getenv("FAST_API", "http://localhost:8000"))

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
        await self._handle_character_add(interaction, name, character_url)

    async def _handle_character_add(
        self, interaction: discord.Interaction, name: str, character_url: str = None
    ):
        """Add a new character for the user."""
        req = AddCharacterRequest(
            player_id=str(interaction.user.id),
            name=name,
            character_url=character_url,
        )
        
        data = await self.api_client.add_character(req)
        await interaction.response.send_message(
            f"Character '{name}' added successfully! (ID: {data.get('character_id')})",
            ephemeral=True,
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
        await self._handle_update(interaction, character_id, name, character_url)

    async def _handle_update(
        self,
        interaction: discord.Interaction,
        character_id: int,
        name: str = None,
        character_url: str = None,
    ):
        """Update character data."""
        from packages.shared.exceptions import ValidationError
        
        if name is None and character_url is None:
            raise ValidationError(
                "CHARACTER_EMPTY_FIELDS",
                details={"message": "You must provide at least one field to update (name or character_url)."}
            )
        
        req = UpdateCharacterRequest(
            character_id=character_id,
            name=name,
            character_url=character_url,
        )
        
        await self.api_client.update_character(req)
        await interaction.response.send_message(
            "Character updated successfully.",
            ephemeral=True,
        )

    @character.command(
        name="remove", description="Remove a character from your account."
    )
    @app_commands.describe(character_id="The ID of the character to remove")
    @discord_error_handler()
    async def remove(self, interaction: discord.Interaction, character_id: int):
        await self._handle_character_remove(interaction, character_id)

    async def _handle_character_remove(
        self, interaction: discord.Interaction, character_id: int
    ):
        """Remove a character."""
        req = RemoveCharacterRequest(character_id=character_id)
        
        await self.api_client.remove_character(req)
        await interaction.response.send_message(
            "Character removed successfully.",
            ephemeral=True,
        )

    @character.command(name="list", description="List all your characters.")
    @discord_error_handler()
    async def list(self, interaction: discord.Interaction):
        """List all characters for the user."""
        req = ListCharactersRequest(player_id=str(interaction.user.id))
        
        data = await self.api_client.list_characters(req)
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
        
        await interaction.response.send_message(msg, ephemeral=True)

    async def cog_load(self):
        """Called when the cog is loaded."""
        pass

    async def cog_unload(self):
        """Called when the cog is unloaded. Clean up resources."""
        await self.api_client.close()


async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
