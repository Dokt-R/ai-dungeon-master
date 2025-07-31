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
    "For more details, see: [Full Getting Started Guide](https://example.com/docs/getting-started)"
)

COST_MESSAGE = (
    "**API Usage Cost Transparency**\n"
    "- The bot uses your own API key (BYOK model) for OpenAI or other LLM providers.\n"
    "- Average cost: ~$0.02–$0.10 per campaign session (varies by model and usage).\n"
    "- No hidden fees. You control your spend.\n"
    "- See the full cost breakdown and real-world examples here: [Cost Documentation](https://example.com/docs/costs)"
)

HELP_MESSAGE = (
    "**Available Commands:**\n"
    "- `/getting-started` — Step-by-step onboarding guide.\n"
    "- `/cost` — API usage cost info and transparency.\n"
    "- `/server-setup` — Explains the BYOK model and how to submit your API key.\n"
    "- `/server-setkey [API_KEY]` — Submit your server’s API key (admin only).\n"
    "- `/ping` — Check if the bot is alive.\n"
    "\n"
    "For advanced help, see [Command Reference](https://github.com/your-org/ai-dungeon-master/blob/main/docs/commands.md)."
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
        message = ("Pong!")
        await interaction.response.send_message(message, ephemeral=True)


    @discord.app_commands.command(
        name="getting-started",
        description="Show a step-by-step onboarding guide for new users and server owners."
    )
    @discord_error_handler()
    async def getting_started(self, interaction: discord.Interaction):
        """Show a step-by-step onboarding guide for new users and server owners."""
        await interaction.response.send_message(ONBOARDING_MESSAGE, ephemeral=True)

    @discord.app_commands.command(
        name="cost",
        description="Show transparent information about average API usage costs and link to documentation."
    )
    @discord_error_handler()
    async def cost(self, interaction: discord.Interaction):
        """Show transparent information about average API usage costs and link to documentation."""
        await interaction.response.send_message(COST_MESSAGE, ephemeral=True)

    @discord.app_commands.command(
        name="help",
        description="List all available commands with brief descriptions and references to advanced help."
    )
    @discord_error_handler()
    async def help(self, interaction: discord.Interaction):
        """List all available commands with brief descriptions and references to advanced help."""
        await interaction.response.send_message(HELP_MESSAGE, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
