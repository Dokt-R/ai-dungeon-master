import discord
from discord.ui import Modal, TextInput


class CharacterCreationModal(Modal, title="Determine your Origin"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.finished = False

    name = TextInput(
        label="Character Name",
        placeholder="Enter your character's name",
        required=True,
    )


    # subclass = TextInput(
    #     label="Subclass",
    #     placeholder="Enter your character's subclass",
    #     required=False,
    # )

    async def on_submit(self, interaction: discord.Interaction):
        self.finished = True
        await interaction.response.defer(ephemeral=True)
        self.stop()

class CharacterNameModal(Modal, title="Name Your Character"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.finished = False

    name = TextInput(
        label="Character Name",
        placeholder="E.g., Eldrin, Lia, etc.",
        required=True,
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.finished = True
        await interaction.response.defer()
        self.stop()
