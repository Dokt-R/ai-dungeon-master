import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from packages.shared.api_client import ApiClient
from packages.shared.error_handler import discord_error_handler
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import (
    AIAPIError,
    CustomException,
    NotFoundError,
    ValidationError,
)

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


# Test commands for error handling validation
class AITestCog(commands.Cog):
    """Test commands for error handling validation"""

    def __init__(self, bot):
        self.bot = bot
        self.api_client = ApiClient(
            base_url=os.getenv("FAST_API", "http://localhost:8000")
        )

    health = app_commands.Group(
        name="ai", description="AI Test Commands"
    )

    async def cog_load(self):
        """Called when the cog is loaded."""
        pass

    async def cog_unload(self):
        """Called when the cog is unloaded. Clean up resources."""
        await self.api_client.close()

    @health.command(
        name="test", description="Check the response of the AI system."
    )
    @app_commands.describe()
    @discord_error_handler()
    async def ai_test_(self,
        interaction: discord.Interaction,
        action: str,
        session_id: Optional[str] = None,
        campaign_context: Optional[str] = None,
    ) -> None:
        """
        Submit an action to the AI Dungeon Master for narrative response.

        Args:
            interaction: Discord interaction
            action: The player's action or command
            session_id: Optional session identifier
            campaign_context: Optional campaign context
        """
        await self._handle_ai_test(
            interaction, action, session_id, campaign_context
        )

    async def _handle_ai_test(
        self,
        interaction: discord.Interaction,
        action: str,
        session_id: Optional[str] = None,
        campaign_context: Optional[str] = None,
    ) -> None:
        """Handle action submission to AI DM."""
        try:
            await interaction.response.defer(ephemeral=True)

            # Generate session ID if not provided
            if not session_id:
                session_id = (
                    f"{interaction.guild_id}_{interaction.user.id}_{interaction.id}"
                )

            # Prepare action data
            action_data = {
                "session_id": session_id,
                "user_id": str(interaction.user.id),
                "prompt": action,
                "metadata": {
                    "discord_guild_id": str(interaction.guild_id),
                    "discord_channel_id": str(interaction.channel_id),
                    "discord_user_id": str(interaction.user.id),
                    "discord_username": interaction.user.name,
                    "timestamp": interaction.created_at.isoformat(),
                },
            }

            # Add campaign context if provided
            if campaign_context:
                action_data["campaign_context"] = campaign_context

            # Submit action to AI DM
            response = await self.api_client.submit_action(action_data)

            # Store active session
            self._active_sessions[interaction.guild_id] = session_id

            # Create response embed
            embed = discord.Embed(
                title="🎭 AI Dungeon Master Response",
                color=discord.Color.blue(),
                description=response.get(
                    "narrative", "The DM responds with a narrative continuation..."
                ),
            )

            embed.add_field(
                name="🎯 Your Action",
                value=action[:1024],  # Discord field limit
                inline=False,
            )

            embed.add_field(name="⏱️ Processing Time", value=".2f", inline=True)

            embed.add_field(name="🔢 Session ID", value=session_id, inline=True)

            embed.add_field(
                name="📊 Status",
                value=response.get("status", "unknown").title(),
                inline=True,
            )

            # Add metadata if available
            if "metadata" in response and "generated_at" in response["metadata"]:
                embed.set_footer(
                    text=f"Generated at: {response['metadata']['generated_at']}"
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

            self.logger.info(
                "Action submitted successfully",
                session_id=session_id,
                user_id=interaction.user.id,
                action_length=len(action),
                response_length=len(response.get("narrative", "")),
            )

        except Exception as e:
            self.logger.error(
                "Failed to submit action",
                error=str(e),
                user_id=interaction.user.id,
                action=action[:100],  # Log first 100 chars
            )

            await interaction.followup.send(
                f"❌ Failed to submit action to AI DM: {str(e)}", ephemeral=True
            )


async def setup_ai_test(bot):
    await bot.add_cog(AITestCog(bot))