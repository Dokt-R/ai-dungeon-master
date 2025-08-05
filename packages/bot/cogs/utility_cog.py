import discord
from discord.ext import commands
from packages.shared.error_handler import (
    handle_error,
    ValidationError,
    NotFoundError,
    discord_error_handler,
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
    async def help(self, interaction: discord.Interaction, topic: str = None):
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
