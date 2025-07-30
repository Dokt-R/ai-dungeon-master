import discord
from discord.ext import commands
from packages.shared.error_handler import handle_error, ValidationError, NotFoundError


class UtilityCog(commands.Cog):
    """Utility commands such as /ping."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Optional: can be used for cog-specific ready logic
        pass

    @discord.app_commands.command(name="ping", description="Check if the bot is alive")
    async def ping(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Pong!")
        except Exception as e:
            handle_error(e)
            await interaction.response.send_message(
                "An unexpected error occurred while processing your request.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
