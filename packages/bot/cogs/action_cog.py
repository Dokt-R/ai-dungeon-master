"""
Action Cog for AI Dungeon Master Discord Bot.

This cog handles player actions and interactions with the AI Dungeon Master,
providing commands to submit actions, test endpoints, and manage narrative flow.
"""

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from packages.shared.api_client import ApiClient
from packages.shared.error_handler import discord_error_handler
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class ActionCog(commands.Cog):
    """
    Discord.py cog for handling player actions and AI DM interactions.

    Provides commands for submitting narrative actions, testing endpoints,
    and managing the AI Dungeon Master's response system.
    """

    def __init__(self, bot: commands.Bot, api_base_url: str = "http://localhost:8000"):
        """Initialize the Action Cog."""
        self.bot = bot
        self.logger = get_logger(f"{__name__}.ActionCog")
        # Use longer timeout for AI actions (they can take 15-20 seconds)
        self.api_client = ApiClient(api_base_url, timeout=45.0)

        # Track active sessions per guild
        self._active_sessions: dict[int, str] = {}  # guild_id -> session_id

        self.logger.info("ActionCog initialized")

    action = app_commands.Group(
        name="action", description="AI Dungeon Master action commands"
    )

    @action.command(
        name="submit", description="Submit an action to the AI Dungeon Master"
    )
    @app_commands.describe(
        action="Your action or command for the AI DM",
        session_id="Optional: Specific session ID (auto-generated if not provided)",
        campaign_context="Optional: Campaign context information",
    )
    @discord_error_handler()
    async def submit(
        self,
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
        await self._handle_action_submit(
            interaction, action, session_id, campaign_context
        )

    async def _handle_action_submit(
        self,
        interaction: discord.Interaction,
        action: str,
        session_id: Optional[str] = None,
        campaign_context: Optional[str] = None,
    ) -> None:
        """Handle action submission to AI DM."""
        try:
            await interaction.response.defer(ephemeral=True)

            # Send a quick acknowledgment that we're processing
            await interaction.followup.send(
                "🎲 Processing your action with the AI DM... This may take 10-20 seconds for complex responses.",
                ephemeral=True,
            )

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

            # Check if the response indicates an error
            if response.get("status") == "error":
                error_msg = response.get("error", "Unknown error occurred")
                await interaction.edit_original_response(
                    content=f"❌ The AI DM encountered an issue: {error_msg}",
                    embed=None,
                )
                return

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

            embed.add_field(
                name="⏱️ Processing Time",
                value=f"{response.get('processing_time', 0):.2f}s",
                inline=True,
            )

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

            # Edit the processing message with the final response
            await interaction.edit_original_response(content=None, embed=embed)

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
                error_type=type(e).__name__,
                user_id=interaction.user.id,
                action=action[:100],  # Log first 100 chars
            )

            error_message = str(e) if str(e) else f"Unknown error ({type(e).__name__})"

            # Provide a more user-friendly error message based on error type
            if (
                "ReadTimeout" in str(type(e).__name__)
                or "timeout" in error_message.lower()
            ):
                user_message = "⏳ The AI DM is taking longer than usual to respond. This is normal for complex actions. Please wait a moment and try again if needed."
            elif "connection" in error_message.lower():
                user_message = "❌ Unable to connect to the AI DM. The service may be temporarily unavailable."
            elif "validation" in error_message.lower():
                user_message = "❌ Your action couldn't be processed. Please check your input and try again."
            elif not error_message.strip():
                user_message = (
                    "❌ The AI DM service encountered an issue. Please try again."
                )
            else:
                user_message = f"❌ Failed to submit action to AI DM: {error_message}"

            await interaction.edit_original_response(content=user_message, embed=None)

    @action.command(
        name="test", description="Test the action API endpoint connectivity"
    )
    @app_commands.describe()
    @discord_error_handler()
    async def test(self, interaction: discord.Interaction) -> None:
        """
        Test the action API endpoint to verify connectivity.

        Args:
            interaction: Discord interaction
        """
        await self._handle_action_test(interaction)

    async def _handle_action_test(self, interaction: discord.Interaction) -> None:
        """Handle action API test request."""
        try:
            await interaction.response.defer(ephemeral=True)

            # Test the action endpoint
            test_result = await self.api_client.test_action_endpoint()

            embed = discord.Embed(
                title="🧪 Action API Test",
                color=discord.Color.green()
                if test_result.get("status") == "success"
                else discord.Color.red(),
            )

            embed.add_field(
                name="📊 Status",
                value=test_result.get("status", "unknown").title(),
                inline=True,
            )

            embed.add_field(
                name="🔗 Endpoint",
                value=test_result.get("endpoint", "unknown"),
                inline=True,
            )

            embed.add_field(
                name="🧪 Test Endpoint",
                value=test_result.get("test_endpoint", "unknown"),
                inline=True,
            )

            if "message" in test_result:
                embed.add_field(
                    name="📝 Message", value=test_result["message"], inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

            self.logger.info(
                "Action API test completed",
                user_id=interaction.user.id,
                status=test_result.get("status"),
            )

        except Exception as e:
            self.logger.error(
                "Failed to test action API", error=str(e), user_id=interaction.user.id
            )

            await interaction.followup.send(
                f"❌ Failed to test action API: {str(e)}", ephemeral=True
            )

    @action.command(
        name="info",
        description="Get information about the current action session",
    )
    @app_commands.describe()
    @discord_error_handler()
    async def session_info(self, interaction: discord.Interaction) -> None:
        """
        Get information about the current action session for this guild.

        Args:
            interaction: Discord interaction
        """
        await self._handle_session_info(interaction)

    async def _handle_session_info(self, interaction: discord.Interaction) -> None:
        """Handle session info request."""
        try:
            await interaction.response.defer(ephemeral=True)

            session_id = self._active_sessions.get(interaction.guild_id)

            if not session_id:
                await interaction.followup.send(
                    "📝 No active action session found for this server.\n"
                    "Use `/action_submit` to start a new session with the AI DM.",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="📊 Action Session Info",
                color=discord.Color.blue(),
                description=f"**Session ID:** `{session_id}`",
            )

            embed.add_field(name="🏰 Guild", value=interaction.guild.name, inline=True)

            embed.add_field(
                name="👥 Initiated By", value=f"<@{interaction.user.id}>", inline=True
            )

            embed.add_field(
                name="📅 Active Since",
                value=f"<t:{int(interaction.created_at.timestamp())}:R>",
                inline=True,
            )

            embed.add_field(
                name="💡 Usage Tip",
                value="Submit actions using `/action_submit` with your narrative commands!",
                inline=False,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(
                "Failed to get action session info",
                error=str(e),
                guild_id=interaction.guild_id,
                user_id=interaction.user.id,
            )

            await interaction.followup.send(
                f"❌ Failed to get session information: {str(e)}", ephemeral=True
            )

    @action.command(name="help", description="Get help with AI DM action commands")
    @app_commands.describe()
    @discord_error_handler()
    async def help(self, interaction: discord.Interaction) -> None:
        """
        Provide help and examples for using AI DM action commands.

        Args:
            interaction: Discord interaction
        """
        await self._handle_help(interaction)

    async def _handle_help(self, interaction: discord.Interaction) -> None:
        """Handle help request."""
        try:
            await interaction.response.defer(ephemeral=True)

            embed = discord.Embed(
                title="🎭 AI Dungeon Master - Action Commands",
                color=discord.Color.gold(),
                description="Learn how to interact with the AI Dungeon Master!",
            )

            embed.add_field(
                name="📝 Submit Action",
                value='`/action submit action:"I swing my sword at the goblin"`\n'
                "Submit actions, dialogue, or commands to the AI DM",
                inline=False,
            )

            embed.add_field(
                name="🔧 Advanced Options",
                value="• `session_id`: Custom session tracking\n"
                "• `campaign_context`: Additional campaign info",
                inline=False,
            )

            embed.add_field(
                name="📋 Action Examples",
                value='• `"I attack the dragon with my magic sword"`\n'
                '• `"I talk to the mysterious stranger"`\n'
                '• `"I search the ancient chest"`\n'
                '• `"I cast fireball at the enemy group"`',
                inline=False,
            )

            embed.add_field(
                name="🧪 Testing",
                value="`/action test` - Verify API connectivity\n"
                "`/action info` - View current session",
                inline=False,
            )

            embed.add_field(
                name="💡 Tips",
                value="• Be descriptive in your actions\n"
                "• The AI DM will respond with narrative continuation\n"
                "• Include dialogue, combat, exploration, or any adventure action!",
                inline=False,
            )

            embed.set_footer(
                text="The AI DM will respond with rich narrative based on your actions!"
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(
                "Failed to show action help", error=str(e), user_id=interaction.user.id
            )

            await interaction.followup.send(
                f"❌ Failed to show help: {str(e)}", ephemeral=True
            )

    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        pass

    async def cog_unload(self) -> None:
        """Clean up when cog is unloaded."""
        try:
            # Clear session tracking
            self._active_sessions.clear()

            # Close API client
            try:
                await self.api_client.close()
            except Exception as e:
                self.logger.error("Error closing API client", error=str(e))

            self.logger.info("ActionCog unloaded successfully")

        except Exception as e:
            self.logger.error("Error during ActionCog unload", error=str(e))


async def setup(bot: commands.Bot) -> None:
    """Setup function for the action cog."""
    await bot.add_cog(ActionCog(bot))
