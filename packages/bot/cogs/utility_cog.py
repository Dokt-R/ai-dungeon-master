import os
import time
from typing import Optional
from contextlib import asynccontextmanager

import discord
from discord import app_commands
from discord.ext import commands
from langsmith import traceable

from packages.shared.api_client import ApiClient
from packages.shared.error_handler import discord_error_handler
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import (
    AIAPIError,
    CustomException,
    NotFoundError,
    ValidationError,
)
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

# Create logger for timing and performance tracking
logger = get_logger(__name__)

# Message constants for maintainability
ONBOARDING_MESSAGE = (
    "Welcome to the AI Dungeon Master Bot! Here’s how to get started:\n"
    "1. **Invite the bot** to your server using the official invite link.\n"
    "2. **Set up your server’s API key** (BYOK model) with `/server-setup` and `/server-setkey`.\n"
    "3. **Start a campaign** by using the campaign commands.\n"
    "4. **Need help?** Use `/help` for a list of commands or visit the documentation.\n"
    "For more details, see: [Full Getting Started Guide](https://github.com/Dokt-R/ai-dungeon-master/blob/main/docs/getting-started.md)"
)

COST_MESSAGE = (
    "**API Usage Cost Transparency**\n"
    "- The bot uses your own API key (BYOK model) for OpenAI or other LLM providers.\n"
    "- Average cost: ~$0.02–$0.10 per campaign session (varies by model and usage).\n"
    "- No hidden fees. You control your spend.\n"
    "- See the full cost breakdown and real-world examples here: [Cost Documentation](https://github.com/Dokt-R/ai-dungeon-master/blob/main/docs/costs.md)"
)

HELP_TOPICS = {
    "campaign": (
        "**Campaign Commands Help**\n"
        "- `/campaign-create` — Start a new campaign with a title and description.\n"
        "- `/campaign-join` — Join an existing campaign by code or invite.\n"
        "- `/campaign-list` — List all campaigns you are part of.\n"
        "- `/campaign-leave` — Leave a campaign.\n"
        "For more, see [Campaign Guide](https://github.com/Dokt-R/ai-dungeon-master/blob/main/docs/campaigns.md)"
    ),
    "setup": (
        "**Setup Help**\n"
        "- `/server-setup` — Explains the BYOK model and how to submit your API key.\n"
        "- `/server-setkey [API_KEY]` — Submit your server’s API key (admin only).\n"
        "See [Setup Guide](https://github.com/Dokt-R/ai-dungeon-master/blob/main/docs/getting-started.md)"
    ),
}

HELP_TOPIC_LIST = (
    "**Help Topics:**\n"
    "- `campaign` — Learn about campaign management commands.\n"
    "- `setup` — Learn how to set up the bot and API keys.\n"
    "\n"
    "Type `/help <topic>` for detailed help on a topic.\n"
    "Example: `/help campaign`"
)

HELP_MESSAGE = (
    "**Available Commands:**\n"
    "- `/getting-started` — Step-by-step onboarding guide.\n"
    "- `/cost` — API usage cost info and transparency.\n"
    "- `/server-setup` — Explains the BYOK model and how to submit your API key.\n"
    "- `/server-setkey [API_KEY]` — Submit your server’s API key (admin only).\n"
    "- `/ping` — Check if the bot is alive.\n"
    "\n"
    "For advanced help, see [Command Reference](https://github.com/Dokt-R/ai-dungeon-master/blob/main/docs/commands.md).\n"
    "\n"
    "For help topics, type `/help`."
)


class UtilityCog(commands.Cog):
    """Utility commands such as /ping."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Optional: can be used for cog-specific ready logic
        pass

    @discord.app_commands.command(name="ping", description="Check if the bot is alive")
    @discord_error_handler()
    async def ping(self, interaction: discord.Interaction):
        message = "Pong!"
        await interaction.response.send_message(message, ephemeral=True)

    @discord.app_commands.command(
        name="getting-started",
        description="Show a step-by-step onboarding guide for new users and server owners.",
    )
    @discord_error_handler()
    async def getting_started(self, interaction: discord.Interaction):
        """Show a step-by-step onboarding guide for new users and server owners."""
        await interaction.response.send_message(ONBOARDING_MESSAGE, ephemeral=True)

    @discord.app_commands.command(
        name="cost",
        description="Show transparent information about average API usage costs and link to documentation.",
    )
    @discord_error_handler()
    async def cost(self, interaction: discord.Interaction):
        """Show transparent information about average API usage costs and link to documentation."""
        await interaction.response.send_message(COST_MESSAGE, ephemeral=True)

    @discord.app_commands.command(
        name="help",
        description="List all available commands, or get detailed help for a topic.",
    )
    @discord.app_commands.describe(
        topic="Optional: Get detailed help for a specific topic (e.g., campaign, setup)"
    )
    @discord_error_handler()
    async def help(self, interaction: discord.Interaction, topic: Optional[str] = None):
        """List all available commands, or get detailed help for a topic."""
        if topic is None:
            # List help topics
            await interaction.response.send_message(
                f"{HELP_MESSAGE}\n\n{HELP_TOPIC_LIST}", ephemeral=True
            )
        else:
            topic_key = topic.lower().strip()
            if topic_key in HELP_TOPICS:
                await interaction.response.send_message(
                    HELP_TOPICS[topic_key], ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Unknown help topic: `{topic}`.\n\n{HELP_TOPIC_LIST}",
                    ephemeral=True,
                )

    @discord.app_commands.command(
        name="templates",
        description="Show examples of Discord's rich interactive features for RPGs",
    )
    @discord_error_handler()
    async def templates(self, interaction: discord.Interaction):
        """Show comprehensive examples of Discord's interactive features for RPGs."""

        # Create the main embed with character sheet example
        embed = discord.Embed(
            title="🧙‍♂️ Gandalf the Grey",
            description="*A wise wizard of great power and knowledge*",
            color=discord.Color.blue(),
        )

        # Add character stats as fields (simulating a table)
        embed.add_field(name="💪 Strength", value="12", inline=True)
        embed.add_field(name="🏃 Dexterity", value="14", inline=True)
        embed.add_field(name="🧠 Intelligence", value="18", inline=True)
        embed.add_field(name="🔍 Wisdom", value="16", inline=True)
        embed.add_field(name="💬 Charisma", value="15", inline=True)
        embed.add_field(name="💪 Constitution", value="13", inline=True)

        # Add status information
        embed.add_field(name="❤️ Health", value="45/50 HP", inline=True)
        embed.add_field(name="✨ Mana", value="30/35 MP", inline=True)
        embed.add_field(name="⭐ Level", value="10", inline=True)

        # Add equipment section
        embed.add_field(
            name="⚔️ Equipment",
            value="🪄 Staff of Power\n🧥 Robes of the Archmagi\n💍 Ring of Protection",
            inline=False,
        )

        # Add a code block table example
        embed.add_field(
            name="📊 Combat Stats Table",
            value="```\n| Stat    | Value | Modifier |\n|---------|-------|----------|\n| AC      |   15  |    +2    |\n| Speed   |   30  |    +0    |\n| Init    |   +2  |    +2    |\n```",
            inline=False,
        )

        # Set thumbnail (character portrait)
        embed.set_thumbnail(
            url="https://via.placeholder.com/150x150/4A90E2/FFFFFF?text=🧙‍♂️"
        )

        # Add footer with timestamp
        embed.set_footer(
            text="Last updated",
            icon_url="https://via.placeholder.com/20x20/28A745/FFFFFF?text=✓",
        )
        embed.timestamp = discord.utils.utcnow()

        # Create interactive buttons
        view = TemplateView()

        await interaction.response.send_message(
            "## 🎲 Discord RPG Interface Examples\n"
            "Here are examples of Discord's rich interactive features perfect for RPGs:\n\n"
            "**1. Rich Embeds** - Character sheets, item cards, stat summaries\n"
            "**2. Interactive Buttons** - Actions, spells, items (try the buttons below!)\n"
            "**3. Select Menus** - Choose from lists of spells, weapons, actions\n"
            "**4. Modal Forms** - Level-up forms, skill checks, character updates\n"
            "**5. Tables** - Combat stats, inventory, party info\n"
            "**6. Real-time Updates** - Living character sheets that update instantly\n",
            embed=embed,
            view=view,
            ephemeral=True,
        )


# Interactive View class for the templates command
class TemplateView(discord.ui.View):
    """Interactive view showcasing Discord's UI components for RPGs."""

    def __init__(self):
        super().__init__(timeout=300)  # 5 minute timeout

    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Example attack button with dice roll simulation."""
        import random

        # Simulate dice roll
        d20_roll = random.randint(1, 20)
        damage_roll = random.randint(1, 8) + 3  # 1d8+3

        embed = discord.Embed(
            title="⚔️ Attack Roll!",
            description=f"Gandalf swings his staff with magical force!",
            color=discord.Color.red(),
        )
        embed.add_field(
            name="🎲 Attack Roll",
            value=f"d20: **{d20_roll}** (+5 = {d20_roll + 5})",
            inline=True,
        )
        embed.add_field(
            name="💥 Damage", value=f"1d8+3: **{damage_roll}** damage", inline=True
        )
        embed.add_field(
            name="🎯 Result",
            value="Hit!" if d20_roll + 5 >= 15 else "Miss!",
            inline=True,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="✨ Cast Spell", style=discord.ButtonStyle.primary, emoji="✨"
    )
    async def spell_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Example spell button that opens a spell selection menu."""
        view = SpellSelectView()
        await interaction.response.send_message(
            "Choose a spell to cast:", view=view, ephemeral=True
        )

    @discord.ui.button(
        label="🎒 Use Item", style=discord.ButtonStyle.secondary, emoji="🎒"
    )
    async def item_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Example item button that shows inventory."""
        embed = discord.Embed(
            title="🎒 Inventory",
            description="Select an item to use:",
            color=discord.Color.green(),
        )
        embed.add_field(name="🧪 Health Potion", value="Restores 25 HP", inline=False)
        embed.add_field(name="🔮 Mana Potion", value="Restores 15 MP", inline=False)
        embed.add_field(
            name="📜 Scroll of Fireball", value="Casts Fireball spell", inline=False
        )

        view = ItemSelectView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(
        label="📊 Character Sheet", style=discord.ButtonStyle.success, emoji="📊"
    )
    async def character_sheet_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Example button that opens a character update modal."""
        modal = CharacterUpdateModal()
        await interaction.response.send_modal(modal)


class SpellSelectView(discord.ui.View):
    """Example spell selection dropdown menu."""

    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.select(
        placeholder="Choose a spell to cast...",
        options=[
            discord.SelectOption(
                label="Fireball",
                description="3rd level evocation - 8d6 fire damage",
                emoji="🔥",
                value="fireball",
            ),
            discord.SelectOption(
                label="Magic Missile",
                description="1st level evocation - 3 darts of force",
                emoji="✨",
                value="magic_missile",
            ),
            discord.SelectOption(
                label="Heal",
                description="1st level evocation - Restore health",
                emoji="💚",
                value="heal",
            ),
            discord.SelectOption(
                label="Shield",
                description="1st level abjuration - +5 AC",
                emoji="🛡️",
                value="shield",
            ),
        ],
    )
    async def spell_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        """Handle spell selection."""
        import random

        spell_data = {
            "fireball": {"name": "🔥 Fireball", "damage": "8d6", "type": "Fire"},
            "magic_missile": {
                "name": "✨ Magic Missile",
                "damage": "3d4+3",
                "type": "Force",
            },
            "heal": {"name": "💚 Heal", "damage": "1d8+3", "type": "Healing"},
            "shield": {"name": "🛡️ Shield", "damage": "+5 AC", "type": "Protection"},
        }

        selected_spell = spell_data[select.values[0]]

        # Simulate spell effect
        if select.values[0] == "fireball":
            damage = sum(random.randint(1, 6) for _ in range(8))
        elif select.values[0] == "magic_missile":
            damage = sum(random.randint(1, 4) for _ in range(3)) + 3
        elif select.values[0] == "heal":
            damage = random.randint(1, 8) + 3
        else:  # shield
            damage = 5

        embed = discord.Embed(
            title=f"{selected_spell['name']} Cast!",
            description=f"Gandalf casts {selected_spell['name']}!",
            color=discord.Color.purple(),
        )
        embed.add_field(
            name="🎲 Effect",
            value=f"{selected_spell['damage']}: **{damage}**",
            inline=True,
        )
        embed.add_field(name="🔮 Type", value=selected_spell["type"], inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class ItemSelectView(discord.ui.View):
    """Example item selection with buttons."""

    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="🧪 Health Potion", style=discord.ButtonStyle.success)
    async def health_potion(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Use health potion."""
        embed = discord.Embed(
            title="🧪 Health Potion Used!",
            description="Gandalf drinks a health potion and feels refreshed.",
            color=discord.Color.green(),
        )
        embed.add_field(name="💚 Healing", value="+25 HP", inline=True)
        embed.add_field(name="❤️ New Health", value="50/50 HP (Full!)", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔮 Mana Potion", style=discord.ButtonStyle.primary)
    async def mana_potion(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Use mana potion."""
        embed = discord.Embed(
            title="🔮 Mana Potion Used!",
            description="Gandalf drinks a mana potion and feels his magical energy restored.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="✨ Mana Restored", value="+15 MP", inline=True)
        embed.add_field(name="🔮 New Mana", value="35/35 MP (Full!)", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class CharacterUpdateModal(discord.ui.Modal):
    """Example modal form for character updates."""

    def __init__(self):
        super().__init__(title="📊 Update Character Sheet")

    # Text inputs for the modal
    character_name = discord.ui.TextInput(
        label="Character Name",
        placeholder="Enter character name...",
        default="Gandalf the Grey",
        max_length=50,
    )

    hit_points = discord.ui.TextInput(
        label="Current Hit Points",
        placeholder="Enter current HP...",
        default="45",
        max_length=10,
    )

    notes = discord.ui.TextInput(
        label="Character Notes",
        placeholder="Add any notes about your character...",
        style=discord.TextStyle.paragraph,
        default="Wise wizard seeking to protect Middle-earth from the forces of darkness.",
        max_length=500,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        embed = discord.Embed(
            title="✅ Character Updated!",
            description="Your character sheet has been successfully updated.",
            color=discord.Color.green(),
        )
        embed.add_field(name="👤 Name", value=self.character_name.value, inline=True)
        embed.add_field(name="❤️ HP", value=f"{self.hit_points.value}/50", inline=True)
        embed.add_field(
            name="📝 Notes", value=self.notes.value or "No notes", inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))


# Test commands for error handling validation
class ErrorTestCog(commands.Cog):
    """Test commands for error handling validation"""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="test-validation-error", description="Trigger a ValidationError"
    )
    @discord_error_handler()
    async def test_validation_error(self, interaction: discord.Interaction):
        """Trigger a ValidationError"""
        raise ValidationError(ErrorCode.VALIDATION_ERROR)

    @discord.app_commands.command(
        name="test-not-found-error", description="Trigger a NotFoundError"
    )
    @discord_error_handler()
    async def test_not_found_error(self, interaction: discord.Interaction):
        """Trigger a NotFoundError"""
        raise NotFoundError(ErrorCode.NOT_FOUND)

    @discord.app_commands.command(
        name="test-ai-api-error", description="Trigger an AIAPIError"
    )
    @discord_error_handler()
    async def test_ai_api_error(self, interaction: discord.Interaction):
        """Trigger an AIAPIError"""
        raise AIAPIError(ErrorCode.AI_API_ERROR)

    @discord.app_commands.command(
        name="test-generic-error", description="Trigger a generic Exception"
    )
    @discord_error_handler()
    async def test_generic_error(self, interaction: discord.Interaction):
        """Trigger a generic Exception"""
        raise Exception("Test generic error")


async def setup_error_test(bot):
    await bot.add_cog(ErrorTestCog(bot))


# Simple LLM Test Cog
@asynccontextmanager
async def timing_context(operation_name: str, **context_data):
    """Context manager for timing operations and logging performance metrics."""
    start_time = time.perf_counter()
    start_timestamp = time.time()

    logger.info(
        f"{operation_name}_started",
        operation=operation_name,
        timestamp=start_timestamp,
        **context_data,
    )

    try:
        yield start_time
    except Exception as e:
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        logger.error(
            f"{operation_name}_failed",
            operation=operation_name,
            duration_ms=round(duration_ms, 2),
            error=str(e),
            **context_data,
        )
        raise
    else:
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        logger.info(
            f"{operation_name}_completed",
            operation=operation_name,
            duration_ms=round(duration_ms, 2),
            **context_data,
        )


class LLMTestCog(commands.Cog):
    """Simple LLM test commands with comprehensive timing and performance tracking"""

    def __init__(self, bot):
        self.bot = bot
        self.api_client = ApiClient(
            base_url=os.getenv("FAST_API", "http://localhost:8000")
        )

    async def cog_unload(self):
        """Called when the cog is unloaded. Clean up resources."""
        await self.api_client.close()

    @discord.app_commands.command(
        name="llm-test", description="Test the LLM with a simple prompt"
    )
    @app_commands.describe(prompt="The prompt to send to the LLM")
    @discord_error_handler()
    async def llm_test(self, interaction: discord.Interaction, prompt: str) -> None:
        """
        Test the LLM with a simple prompt with comprehensive timing tracking.

        Args:
            interaction: Discord interaction
            prompt: The prompt to send to the LLM
        """
        # Generate unique request ID for tracking
        request_id = f"llm_test_{int(time.time() * 1000)}"
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None

        async with timing_context(
            "llm_test_full_request",
            request_id=request_id,
            user_id=user_id,
            guild_id=guild_id,
            prompt_length=len(prompt),
        ):
            try:
                # Stage 1: Discord interaction defer
                async with timing_context(
                    "discord_interaction_defer", request_id=request_id
                ):
                    await interaction.response.defer(ephemeral=True)

                # Stage 2: API client call
                async with timing_context(
                    "api_client_call", request_id=request_id, prompt_length=len(prompt)
                ) as api_start:
                    response = await self.api_client.test_llm(prompt)

                # Stage 3: Response processing
                async with timing_context(
                    "response_processing",
                    request_id=request_id,
                    response_keys=list(response.keys())
                    if isinstance(response, dict)
                    else "not_dict",
                ):
                    # Extract timing information from response metadata
                    metadata = response.get("metadata", {})
                    response_length = len(response.get("response", ""))

                    # Log response analysis
                    logger.info(
                        "llm_response_analysis",
                        request_id=request_id,
                        response_length=response_length,
                        status=response.get("status", "unknown"),
                        model=metadata.get("model", "unknown"),
                        backend_prompt_length=metadata.get("prompt_length", 0),
                        backend_response_length=metadata.get("response_length", 0),
                    )

                # Stage 4: Discord embed creation
                async with timing_context(
                    "discord_embed_creation",
                    request_id=request_id,
                    response_length=response_length,
                ):
                    # Create response embed with timing information
                    embed = discord.Embed(
                        title="🤖 LLM Test Response",
                        color=discord.Color.green(),
                        description=response.get("response", "No response received"),
                    )

                    embed.add_field(
                        name="📝 Your Prompt",
                        value=prompt[:1024],  # Discord field limit
                        inline=False,
                    )

                    embed.add_field(
                        name="📊 Status",
                        value=response.get("status", "unknown").title(),
                        inline=True,
                    )

                    # Add comprehensive metadata including timing
                    if metadata:
                        stats_text = (
                            f"Model: {metadata.get('model', 'unknown')}\n"
                            f"Response Length: {metadata.get('response_length', 0)} chars\n"
                            f"Request ID: {request_id}"
                        )

                        embed.add_field(
                            name="📈 Stats",
                            value=stats_text,
                            inline=True,
                        )

                    # Add performance footer
                    embed.set_footer(
                        text=f"Request ID: {request_id} | Check logs for detailed timing"
                    )

                # Stage 5: Discord response send
                async with timing_context(
                    "discord_response_send",
                    request_id=request_id,
                    embed_fields=len(embed.fields),
                ):
                    await interaction.followup.send(embed=embed, ephemeral=True)

                # Final success log with overall metrics
                logger.info(
                    "llm_test_success_summary",
                    request_id=request_id,
                    user_id=user_id,
                    guild_id=guild_id,
                    prompt_length=len(prompt),
                    response_length=response_length,
                    status=response.get("status", "unknown"),
                    model=metadata.get("model", "unknown"),
                )

            except Exception as e:
                logger.error(
                    "llm_test_error_summary",
                    request_id=request_id,
                    user_id=user_id,
                    guild_id=guild_id,
                    prompt_length=len(prompt),
                    error_type=type(e).__name__,
                    error_message=str(e),
                )

                # Send error response with request ID for debugging
                await interaction.followup.send(
                    f"❌ Failed to test LLM: {str(e)}\n"
                    f"Request ID: {request_id} (check logs for details)",
                    ephemeral=True,
                )


async def setup_llm_test(bot):
    await bot.add_cog(LLMTestCog(bot))
