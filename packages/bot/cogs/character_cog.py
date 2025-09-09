import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from packages.shared.api_client import ApiClient
from packages.shared.error_handler import discord_error_handler
from packages.shared.models import (
    AddCharacterRequest,
    CreateCharacterRequest,
    ListCharactersRequest,
    RemoveCharacterRequest,
    UpdateCharacterRequest,
)

from .views.character_views import CharacterCreationView


class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_client = ApiClient(
            base_url=os.getenv("FAST_API", "http://localhost:8000")
        )

    character = app_commands.Group(
        name="character", description="Manage your characters"
    )

    async def get_classes(self):
        """Get all available classes from the database."""
        return await self.api_client.get_classes()

    @character.command(name="create", description="Create a new character.")
    @discord_error_handler()
    async def create(self, interaction: discord.Interaction):
        view = await CharacterCreationView(self).async_init()
        await interaction.response.send_message(
            "Begin creating your character:", view=view, ephemeral=True
        )

    @character.command(name="add", description="Add a new character to your account.")
    @app_commands.describe(
        name="The name of your character",
        character_url="Optional: D&D Beyond character sheet URL",
    )
    @discord_error_handler()
    async def add(
        self,
        interaction: discord.Interaction,
        name: str,
        character_url: Optional[str] = None,
    ):
        await self._handle_character_add(interaction, name, character_url)

    async def _handle_character_add(
        self,
        interaction: discord.Interaction,
        name: str,
        character_url: Optional[str] = None,
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

    async def _handle_character_create(
        self,
        interaction: discord.Interaction,
        name: str,
        species: str,
        class_index: str,
        subclass: Optional[str],
        background: str,
    ):
        """Create a new character for the user."""
        req = CreateCharacterRequest(
            player_id=str(interaction.user.id),
            name=name,
            species=species,
            class_index=class_index,
            subclass=subclass,
            background=background,
        )

        data = await self.api_client.create_character(req)
        await interaction.followup.send(
            f"Character '{name}' created successfully! (ID: {data.get('character_id')})",
            ephemeral=True,
        )

    async def _handle_character_create_from_view(
        self, interaction: discord.Interaction, character_data: dict
    ):
        """Create a new character for the user from the view."""
        req = CreateCharacterRequest(**character_data)
        await self.api_client.create_character(req)

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
        name: Optional[str] = None,
        character_url: Optional[str] = None,
    ):
        await self._handle_update(interaction, character_id, name, character_url)

    async def _handle_update(
        self,
        interaction: discord.Interaction,
        character_id: int,
        name: Optional[str] = None,
        character_url: Optional[str] = None,
    ):
        """Update character data."""
        from packages.shared.exceptions import ValidationError

        if name is None and character_url is None:
            from packages.shared.errors import ErrorCode

            raise ValidationError(
                ErrorCode.CHARACTER_EMPTY_FIELDS,
                details={
                    "message": "You must provide at least one field to update (name or character_url)."
                },
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
            char_url = char.get("character_url", "N/A")
            if char_url is None:
                char_url = "N/A"
            msg += f"- ID: {char['character_id']}, Name: {char['name']}, D&D Beyond: {char_url}\n"

        await interaction.response.send_message(msg, ephemeral=True)

    async def cog_load(self):
        """Called when the cog is loaded."""
        pass

    async def cog_unload(self):
        """Called when the cog is unloaded. Clean up resources."""
        await self.api_client.close()


async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
