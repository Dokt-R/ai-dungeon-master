import discord
from discord.ui import Modal, TextInput


class CharacterCreationModal(Modal, title="Create Your Character"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.finished = False

    name = TextInput(
        label="Character Name",
        placeholder="Enter your character's name",
        required=True,
    )

    species = TextInput(
        label="Character Species",
        placeholder="Enter your character's species",
        required=True,
    )

    class_field = TextInput(
        label="Character Class",
        placeholder="Enter your character's class",
        required=True,
    )

    subclass = TextInput(
        label="Subclass",
        default="To Be Developed",
        required=False,
    )

    background = TextInput(
        label="Background",
        placeholder="Enter your character's background",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.finished = True
        await interaction.response.defer(ephemeral=True)
        self.stop()
