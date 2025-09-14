import json
from typing import Any, Dict, List

import discord

from packages.shared.logging_config import get_logger
from packages.shared.models.enum_models import (
    AbilityName,
    SkillName,
)

from ..modals.character_modals import CharacterCreationModal, CharacterNameModal

logger = get_logger(__name__)


class ClassSelect(discord.ui.Select):
    def __init__(self, classes: List[Dict[str, Any]]):
        options = [
            discord.SelectOption(label=c["name"], value=c["index"]) for c in classes
        ]
        super().__init__(placeholder="Choose your character's class", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.character_data["class_index"] = self.values[0]
        await self.view.update_to_background_select()
        await interaction.response.edit_message(
            content="Next, choose your character's background.", view=self.view
        )


class BackgroundSelect(discord.ui.Select):
    def __init__(self, backgrounds: List[Dict[str, Any]]):
        options = [
            discord.SelectOption(label=b["name"], value=b["index"]) for b in backgrounds
        ]
        super().__init__(
            placeholder="Choose your character's background", options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.character_data["background_index"] = self.values[0]
        # MODIFIED: Start equipment selection process
        await self.view.handle_equipment(interaction)


class RacesSelect(discord.ui.Select):
    def __init__(self, races: List[Dict[str, Any]]):
        options = [
            discord.SelectOption(label=s["name"], value=s["index"]) for s in races
        ]
        super().__init__(placeholder="Choose your character's races", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.character_data["races_index"] = self.values[0]
        # MODIFIED: Go to abilities, skipping the old modal
        self.view.update_to_abilities_view_part1()
        await interaction.response.edit_message(
            content="Great! Now, please assign your physical ability scores.",
            view=self.view,
        )


# NEW: Select for equipment choices
class EquipmentChoiceSelect(discord.ui.Select):
    def __init__(
        self, options: list, description: str, choose: int, choice_index: int
    ):
        super().__init__(
            placeholder=description,
            options=options,
            min_values=choose,
            max_values=choose,
            row=choice_index % 4,  # Spread selects across rows
        )
        self.choice_index = choice_index

    async def callback(self, interaction: discord.Interaction):
        self.view.character_data["equipment_selections"][
            self.choice_index
        ] = self.values
        await self.view.handle_equipment(interaction)


# NEW: Select for items within an equipment category
class EquipmentCategorySelect(discord.ui.Select):
    def __init__(
        self,
        options: list,
        category_index: str,
        original_choice_index: int,
        choose: int,
    ):
        super().__init__(
            placeholder=f"Select {choose} from {category_index}",
            options=options,
            min_values=choose,
            max_values=choose,
        )
        self.original_choice_index = original_choice_index
        self.category_index = category_index
        self.choose = choose

    async def callback(self, interaction: discord.Interaction):
        # The user has selected item(s) from a category.
        # We need to format these selections and store them back into the original choice.

        # This replaces the 'category:...' placeholder with one or more 'item:...' strings.
        new_values = [f"item:{val}:1" for val in self.values]

        # Find the original placeholder in the selections list and replace it
        original_selections = self.view.character_data["equipment_selections"][
            self.original_choice_index
        ]
        category_placeholder = f"category:{self.category_index}:{self.choose}"

        final_selections = []
        for s in original_selections:
            if s == category_placeholder:
                final_selections.extend(new_values)
            else:
                final_selections.append(s)

        self.view.character_data["equipment_selections"][
            self.original_choice_index
        ] = final_selections

        # Continue the equipment handling process
        await self.view.handle_equipment(interaction)


class CharacterCreationView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.character_data = {
            "inventory": [],
            "equipment_choices": [],
            "equipment_selections": {},
        }
        self.ability_scores = {}

    async def async_init(self):
        # MODIFIED: Start with a button to get character name
        self.clear_items()
        self.add_item(self.get_name_button())
        return self

    def get_name_button(self):
        button = discord.ui.Button(
            label="Begin Character Creation", style=discord.ButtonStyle.green
        )

        async def callback(interaction: discord.Interaction):
            modal = CharacterNameModal()
            await interaction.response.send_modal(modal)
            await modal.wait()

            if not modal.finished:
                self.stop()
                await interaction.followup.send(
                    "Character creation cancelled.", ephemeral=True
                )
                return

            self.character_data["name"] = modal.name.value
            self.character_data["player_id"] = str(interaction.user.id)

            await self.update_to_class_select()
            await interaction.followup.edit_message(
                (await interaction.original_response()).id,
                content=f"Let's create a character for {modal.name.value}. First, choose a class:",
                view=self,
            )

        button.callback = callback
        return button

    async def update_to_class_select(self):
        self.clear_items()
        classes = await self.cog.get_classes()
        self.add_item(ClassSelect(classes))

    async def update_to_background_select(self):
        self.clear_items()
        backgrounds = await self.cog.get_backgrounds()
        self.add_item(BackgroundSelect(backgrounds))

    # NEW: Equipment handling state machine
    async def handle_equipment(self, interaction: discord.Interaction):
        # This method is the central point for equipment selection.
        # It's called after background is selected, and then recursively for each choice.

        # First time call: populate choices from class and background
        if not self.character_data["equipment_choices"]:
            dnd_class = await self.cog.get_class_by_index(
                self.character_data["class_index"]
            )
            dnd_background = await self.cog.get_background_by_index(
                self.character_data["background_index"]
            )

            # 1. Add guaranteed equipment to inventory
            guaranteed_eq = dnd_class.get("starting_equipment", [])
            if "starting_equipment" in dnd_background:
                guaranteed_eq.extend(dnd_background["starting_equipment"])

            for item_data in guaranteed_eq:
                self.character_data["inventory"].append(
                    {
                        "index": item_data["equipment"]["index"],
                        "quantity": item_data["quantity"],
                    }
                )

            # 2. Get all equipment choices
            choices = dnd_class.get("starting_equipment_options", [])
            if dnd_background.get("starting_equipment_options"):
                choices.extend(dnd_background["starting_equipment_options"])
            self.character_data["equipment_choices"] = choices

        # Find next choice to present to the user
        next_choice_to_present = None
        for i, choice in enumerate(self.character_data["equipment_choices"]):
            if i not in self.character_data["equipment_selections"]:
                next_choice_to_present = (i, choice)
                break

        if next_choice_to_present is None:
            # All choices have been recorded, now process them
            await self.process_equipment_selections(interaction)
            return

        # Present the next choice
        self.clear_items()
        choice_index, choice_data = next_choice_to_present

        options = []
        for o in choice_data["from"]["options"]:
            if o["option_type"] == "counted_reference":
                label = f'{o["count"]}x {o["of"]["name"]}'
                value = f'item:{o["of"]["index"]}:{o["count"]}'
                options.append(discord.SelectOption(label=label, value=value))
            elif o["option_type"] == "choice":
                label = o["choice"]["desc"]
                value = f'category:{o["choice"]["from"]["equipment_category"]["index"]}:{o["choice"]["choose"]}'
                options.append(discord.SelectOption(label=label, value=value))
            elif o["option_type"] == "multiple":
                label = " & ".join([f'{i["of"]["name"]}' for i in o["items"]])
                value = json.dumps(o["items"])
                options.append(discord.SelectOption(label=label, value=f"multiple:{value}"))

        self.add_item(
            EquipmentChoiceSelect(
                options, choice_data["desc"], choice_data["choose"], choice_index
            )
        )
        await interaction.response.edit_message(
            content=f'Equipment Choice: {choice_data["desc"]}', view=self
        )

    async def process_equipment_selections(self, interaction: discord.Interaction):
        # All selections are in self.character_data['equipment_selections']
        # We need to check if any of them are category selections that need another step
        for choice_index, selections in self.character_data[
            "equipment_selections"
        ].items():
            for selection in selections:
                if selection.startswith("category:"):
                    _, category_index, choose = selection.split(":")
                    items = await self.cog.get_equipment_by_category(category_index)
                    options = [
                        discord.SelectOption(label=i["name"], value=i["index"])
                        for i in items
                    ]

                    self.clear_items()
                    self.add_item(
                        EquipmentCategorySelect(
                            options, category_index, choice_index, int(choose)
                        )
                    )
                    await interaction.response.edit_message(
                        content=f"Select from {category_index}", view=self
                    )
                    return  # Stop processing until user picks from the category

        # If we're here, all selections are concrete items. Add them to inventory.
        for _, selections in self.character_data["equipment_selections"].items():
            for selection in selections:
                if selection.startswith("item:"):
                    _, index, quantity = selection.split(":")
                    self.character_data["inventory"].append(
                        {"index": index, "quantity": int(quantity)}
                    )
                elif selection.startswith("multiple:"):
                    items_json = selection.split(":", 1)[1]
                    items = json.loads(items_json)
                    for item in items:
                        self.character_data["inventory"].append(
                            {"index": item["of"]["index"], "quantity": item["count"]}
                        )

        await self.unpack_and_finalize_equipment(interaction)

    async def unpack_and_finalize_equipment(self, interaction: discord.Interaction):
        unpacked_inventory = []
        for item in self.character_data["inventory"]:
            # Assuming cog has a way to identify packs, e.g., by category or a flag
            is_pack = await self.cog.is_equipment_pack(item["index"])
            if is_pack:
                contents = await self.cog.get_pack_contents(item["index"])
                for _ in range(item["quantity"]):
                    unpacked_inventory.extend(contents)
            else:
                unpacked_inventory.append(item)

        self.character_data["inventory"] = unpacked_inventory

        await self.update_to_races_select()
        await interaction.response.edit_message(
            content="Equipment selected. Now select your race.", view=self
        )

    async def update_to_races_select(self):
        self.clear_items()
        races = await self.cog.get_races()
        self.add_item(RacesSelect(races))

    # REMOVED update_to_character_modal and get_start_button

    def get_available_ability_options(self, current_ability_value: str = None):
        all_options = ["15", "14", "13", "12", "10", "8"]
        used_scores = [
            str(v)
            for k, v in self.ability_scores.items()
            if str(v) != current_ability_value
        ]
        available_options_labels = [
            opt for opt in all_options if opt not in used_scores
        ]
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
                content="Finally, select two saving throw proficiencies and your skill proficiencies.",
                view=self,
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
        saving_throw_options = [discord.SelectOption(label=st) for st in saving_throws]
        self.add_item(
            ProficiencySelect(
                saving_throw_options,
                "saving_throws",
                min_values=2,
                max_values=2,
                placeholder="Select 2 Saving Throw Proficiencies",
            )
        )
        skills = sorted([skill.value.replace("_", " ").title() for skill in SkillName])
        skill_options = [discord.SelectOption(label=s) for s in skills]
        self.add_item(
            ProficiencySelect(
                skill_options,
                "skills",
                min_values=0,
                max_values=4,
                placeholder="Select Skill Proficiencies (up to 4)",
            )
        )
        self.add_item(self.get_submit_button())

    def get_submit_button(self):
        button = discord.ui.Button(
            label="Finish Character", style=discord.ButtonStyle.green, row=4
        )

        async def callback(interaction: discord.Interaction):
            if (
                "saving_throws" not in self.character_data
                or len(self.character_data["saving_throws"]) != 2
            ):
                await interaction.response.send_message(
                    "Please select exactly two saving throw proficiencies.",
                    ephemeral=True,
                )
                return
            selected_skills_count = len(self.character_data.get("skills", []))
            if not (0 <= selected_skills_count <= 4):
                await interaction.response.send_message(
                    "Please select between 0 and 4 skill proficiencies.",
                    ephemeral=True,
                )
                return
            await interaction.response.defer()
            proficiency_indices = []
            for p in self.character_data.get("saving_throws", []):
                ability_abbr = AbilityName[p.upper()].value
                proficiency_indices.append(f"saving-throw-{ability_abbr}")
            for p in self.character_data.get("skills", []):
                skill_slug = SkillName[
                    p.upper().replace(" ", "_")
                ].value.replace("_", "-")
                proficiency_indices.append(f"skill-{skill_slug}")

            # MODIFIED: Inventory is already processed and in character_data
            full_character_data = {
                **self.character_data,
                **{k.lower(): int(v) for k, v in self.ability_scores.items()},
                "proficiencies": proficiency_indices,
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
        for option in options:
            option.default = (
                default_value is not None and option.label == str(default_value)
            )
        super().__init__(placeholder=f"Select {ability_name}", options=options)
        self.ability_name = ability_name

    async def callback(self, interaction: discord.Interaction):
        self.view.ability_scores[self.ability_name] = int(self.values[0])
        current_abilities_in_view = [
            item.ability_name
            for item in self.view.children
            if isinstance(item, AbilitySelect)
        ]
        if "Strength" in current_abilities_in_view:
            self.view.update_to_abilities_view_part1()
        else:
            self.view.update_to_abilities_view_part2()
        await interaction.response.edit_message(view=self.view)


class ProficiencySelect(discord.ui.Select):
    def __init__(
        self,
        options: list,
        proficiency_type: str,
        min_values: int,
        max_values: int,
        placeholder: str = None,
    ):
        super().__init__(
            placeholder=placeholder
            or f"Select {min_values}-{max_values} {proficiency_type.replace('_', ' ').title()}",
            min_values=min_values,
            max_values=max_values,
            options=options,
        )
        self.proficiency_type = proficiency_type

    async def callback(self, interaction: discord.Interaction):
        self.view.character_data[self.proficiency_type] = self.values
        await interaction.response.defer()
