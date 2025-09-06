import discord

from packages.shared.logging_config import get_logger
from packages.shared.models.enum_models import AbilityName

from ..modals.character_modals import CharacterCreationModal

logger = get_logger(__name__)


class CharacterCreationView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.character_data = {}
        self.ability_scores = {}
        self.add_item(self.get_start_button())

    def get_start_button(self):
        button = discord.ui.Button(
            label="Create Your Character", style=discord.ButtonStyle.green
        )

        async def callback(interaction: discord.Interaction):
            modal = CharacterCreationModal()
            await interaction.response.send_modal(modal)
            await modal.wait()

            if not modal.finished:
                self.stop()
                await interaction.followup.send(
                    "Character creation cancelled.", ephemeral=True
                )
                return

            self.character_data = {
                "player_id": str(interaction.user.id),
                "name": modal.name.value,
                "species": modal.species.value,
                "class_field": modal.class_field.value,
                "subclass": modal.subclass.value,
                "background": modal.background.value,
            }

            self.update_to_abilities_view_part1()
            await interaction.followup.edit_message(
                (await interaction.original_response()).id,
                content="Great! Now, please assign your physical ability scores.",
                view=self,
            )

        button.callback = callback
        return button

    def get_available_ability_options(self, current_ability_value: str = None):
        all_options = ["15", "14", "13", "12", "10", "8"]
        # Exclude the current ability's value from used scores when generating options for its own dropdown
        used_scores = [
            str(v)
            for k, v in self.ability_scores.items()
            if str(v) != current_ability_value
        ]

        available_options_labels = [
            opt for opt in all_options if opt not in used_scores
        ]

        # Ensure the current ability's value is always an option for its own dropdown
        if (
            current_ability_value is not None
            and current_ability_value not in available_options_labels
        ):
            available_options_labels.insert(0, current_ability_value)

        return [discord.SelectOption(label=opt) for opt in available_options_labels]

    def update_to_abilities_view_part1(self):
        self.clear_items()
        abilities = ["Strength", "Dexterity", "Constitution"]
        for ability in abilities:
            current_value = self.ability_scores.get(ability)
            self.add_item(
                AbilitySelect(
                    ability,
                    self.get_available_ability_options(str(current_value)),
                    default_value=current_value,
                )
            )
        self.add_item(self.get_next_abilities_button())

    def get_next_abilities_button(self):
        button = discord.ui.Button(
            label="Next (Mental Abilities)", style=discord.ButtonStyle.primary, row=4
        )

        async def callback(interaction: discord.Interaction):
            if len(self.ability_scores) < 3:
                await interaction.response.send_message(
                    "Please assign a score to all three physical abilities before proceeding.",
                    ephemeral=True,
                )
                return

            self.clear_items()
            self.update_to_abilities_view_part2()
            await interaction.response.edit_message(
                content="Excellent. Now, assign your mental ability scores.", view=self
            )

        button.callback = callback
        return button

    def update_to_abilities_view_part2(self):
        self.clear_items()
        abilities = ["Intelligence", "Wisdom", "Charisma"]
        for ability in abilities:
            current_value = self.ability_scores.get(ability)
            self.add_item(
                AbilitySelect(
                    ability,
                    self.get_available_ability_options(str(current_value)),
                    default_value=current_value,
                )
            )
        self.add_item(self.get_next_proficiencies_button())

    def get_next_proficiencies_button(self):
        button = discord.ui.Button(
            label="Next (Proficiencies)", style=discord.ButtonStyle.primary, row=4
        )

        async def callback(interaction: discord.Interaction):
            if len(self.ability_scores) < 6:
                await interaction.response.send_message(
                    "Please assign a score to all six abilities before proceeding.",
                    ephemeral=True,
                )
                return

            self.clear_items()
            self.update_to_proficiencies_view()
            await interaction.response.edit_message(
                content="Finally, select two saving throw proficiencies.", view=self
            )

        button.callback = callback
        return button

    def update_to_proficiencies_view(self):
        self.clear_items()
        saving_throws = [
            "Strength",
            "Dexterity",
            "Constitution",
            "Intelligence",
            "Wisdom",
            "Charisma",
        ]
        options = [discord.SelectOption(label=st) for st in saving_throws]
        self.add_item(ProficiencySelect(options))
        self.add_item(self.get_submit_button())

    def get_submit_button(self):
        button = discord.ui.Button(
            label="Finish Character", style=discord.ButtonStyle.green, row=4
        )

        async def callback(interaction: discord.Interaction):
            if (
                "proficiencies" not in self.character_data
                or len(self.character_data["proficiencies"]) != 2
            ):
                await interaction.response.send_message(
                    "Please select exactly two saving throw proficiencies.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # Initialize all proficiencies to False
            # Initialize all proficiencies to False
            proficiency_data = {
                f"prof_{ability.value}_save": False for ability in AbilityName
            }

            # Set selected proficiencies to True
            for p in self.character_data["proficiencies"]:
                # Map full ability name to its abbreviated form using the enum
                abbreviated_name = AbilityName[p.upper()].value
                proficiency_data[f"prof_{abbreviated_name}_save"] = True

            full_character_data = {
                **self.character_data,
                **{k.lower(): int(v) for k, v in self.ability_scores.items()},
                **proficiency_data,
            }

            logger.debug(
                "full_character_data_before_api_call", data=full_character_data
            )

            try:
                await self.cog._handle_character_create_from_view(
                    interaction, full_character_data
                )
                self.stop()
                await interaction.edit_original_response(
                    content=f"Character '{self.character_data['name']}' has been created successfully!",
                    view=None,
                )
            except Exception as e:
                self.stop()
                await interaction.edit_original_response(
                    content=f"An error occurred during character creation: {e}",
                    view=None,
                )

        button.callback = callback
        return button


class AbilitySelect(discord.ui.Select):
    def __init__(self, ability_name: str, options: list, default_value: str = None):
        # Set the default property on the options themselves
        for option in options:
            if default_value is not None and option.label == str(default_value):
                option.default = True
            else:
                option.default = False  # Ensure other options are not default

        super().__init__(
            placeholder=f"Select {ability_name}",
            options=options,
        )
        self.ability_name = ability_name

    async def callback(self, interaction: discord.Interaction):
        old_value = self.view.ability_scores.get(self.ability_name)
        new_value = self.values[0]

        self.view.ability_scores[self.ability_name] = int(new_value)

        # Re-render the view to update other dropdowns and reflect the selection
        # Determine which part of the abilities view is currently active
        current_abilities_in_view = [
            item.ability_name
            for item in self.view.children
            if isinstance(item, AbilitySelect)
        ]

        if "Strength" in current_abilities_in_view:  # We are in part 1
            self.view.update_to_abilities_view_part1()
        elif "Intelligence" in current_abilities_in_view:  # We are in part 2
            self.view.update_to_abilities_view_part2()

        await interaction.response.edit_message(view=self.view)


class ProficiencySelect(discord.ui.Select):
    def __init__(self, options: list):
        super().__init__(
            placeholder="Select 2 Saving Throw Proficiencies",
            min_values=2,
            max_values=2,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.character_data["proficiencies"] = self.values
        await interaction.response.defer()
