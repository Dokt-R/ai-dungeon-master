import discord
from discord.ext import commands
from packages.shared.error_handler import handle_error, ValidationError, NotFoundError, discord_error_handler


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
        await interaction.response.send_message("Pong!")


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
