"""
Health monitoring cog for Discord bot.

Provides commands to check the health status of various system components
including AI services, observability, and general system health.
"""

import os

import discord
from discord import app_commands
from discord.ext import commands

from packages.shared.api_client import ApiClient
from packages.shared.error_handler import discord_error_handler
from packages.shared.exceptions import CustomException


class HealthCog(commands.Cog):
    """Health monitoring commands for system status checks."""

    def __init__(self, bot):
        self.bot = bot
        self.api_client = ApiClient(
            base_url=os.getenv("FAST_API", "http://localhost:8000")
        )

    health = app_commands.Group(
        name="health", description="Check system health and status"
    )

    async def cog_load(self):
        """Called when the cog is loaded."""
        pass

    async def cog_unload(self):
        """Called when the cog is unloaded. Clean up resources."""
        await self.api_client.close()

    @health.command(
        name="ai", description="Check the comprehensive health status of the AI system."
    )
    @app_commands.describe()
    @discord_error_handler()
    async def ai(self, interaction: discord.Interaction):
        """Check AI system health including provider, model, tracing, and prompt system."""
        await self._handle_ai_health_check(interaction)

    async def _handle_ai_health_check(self, interaction: discord.Interaction):
        """Handle AI health check request."""
        try:
            # Defer response since health checks might take time
            await interaction.response.defer(ephemeral=True)

            async with self.api_client as client:
                health_data = await client.get_ai_health()

            # Format the response based on health status
            status = health_data.get("status", "unknown")
            provider = health_data.get("provider", "unknown")
            model = health_data.get("model", "unknown")
            traced = health_data.get("traced", False)

            # Create status emoji
            status_emoji = (
                "🟢" if status == "healthy" else "🟡" if status == "degraded" else "🔴"
            )

            embed = discord.Embed(
                title=f"{status_emoji} AI System Health",
                color=discord.Color.green()
                if status == "healthy"
                else discord.Color.yellow()
                if status == "degraded"
                else discord.Color.red(),
            )

            embed.add_field(name="Status", value=status.title(), inline=True)
            embed.add_field(name="Provider", value=provider.title(), inline=True)
            embed.add_field(name="Model", value=model, inline=True)
            embed.add_field(
                name="Tracing",
                value="✅ Active" if traced else "❌ Inactive",
                inline=True,
            )

            # Add prompt system info if available
            if "prompt_system" in health_data:
                prompt_status = health_data["prompt_system"].get("status", "unknown")
                template_count = health_data["prompt_system"].get("template_count", 0)
                embed.add_field(
                    name="Prompt System",
                    value=f"{prompt_status.title()} ({template_count} templates)",
                    inline=True,
                )

            # Add connection test info if available
            if "connection_test" in health_data:
                connection = health_data["connection_test"]
                embed.add_field(
                    name="Connection Test", value=connection.title(), inline=True
                )

            # Add circuit breaker state if available
            if "circuit_breaker_state" in health_data:
                cb_state = health_data["circuit_breaker_state"]
                embed.add_field(
                    name="Circuit Breaker", value=cb_state.title(), inline=True
                )

            # Add timestamp
            if "timestamp" in health_data:
                embed.set_footer(text=f"Checked at: {health_data['timestamp']}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except CustomException as e:
            await interaction.followup.send(
                f"❌ Failed to check AI health: {str(e)}", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Unexpected error checking AI health: {str(e)}", ephemeral=True
            )

    @health.command(
        name="observability",
        description="Check the health status of the observability service.",
    )
    @app_commands.describe()
    @discord_error_handler()
    async def observability(self, interaction: discord.Interaction):
        """Check observability service health including tracing configuration."""
        await self._handle_observability_health_check(interaction)

    async def _handle_observability_health_check(
        self, interaction: discord.Interaction
    ):
        """Handle observability health check request."""
        try:
            await interaction.response.defer(ephemeral=True)

            async with self.api_client as client:
                health_data = await client.get_observability_health()

            status = health_data.get("status", "unknown")
            provider = health_data.get("provider", "unknown")
            project = health_data.get("project", "unknown")

            status_emoji = "🟢" if status == "healthy" else "🔴"
            color = (
                discord.Color.green() if status == "healthy" else discord.Color.red()
            )

            embed = discord.Embed(
                title=f"{status_emoji} Observability Health", color=color
            )

            embed.add_field(name="Status", value=status.title(), inline=True)
            embed.add_field(name="Provider", value=provider.title(), inline=True)
            embed.add_field(name="Project", value=project, inline=True)

            if "error" in health_data and health_data["error"]:
                embed.add_field(name="Error", value=health_data["error"], inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except CustomException as e:
            await interaction.followup.send(
                f"❌ Failed to check observability health: {str(e)}", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Unexpected error checking observability health: {str(e)}",
                ephemeral=True,
            )

    @health.command(
        name="general",
        description="Check the overall health status of the application.",
    )
    @app_commands.describe()
    @discord_error_handler()
    async def general(self, interaction: discord.Interaction):
        """Check general application health including all components."""
        await self._handle_general_health_check(interaction)

    async def _handle_general_health_check(self, interaction: discord.Interaction):
        """Handle general health check request."""
        try:
            await interaction.response.defer(ephemeral=True)

            async with self.api_client as client:
                health_data = await client.get_general_health()

            status = health_data.get("status", "unknown")
            service = health_data.get("service", "unknown")
            version = health_data.get("version", "unknown")

            status_emoji = (
                "🟢" if status == "healthy" else "🟡" if status == "degraded" else "🔴"
            )
            color = (
                discord.Color.green()
                if status == "healthy"
                else discord.Color.yellow()
                if status == "degraded"
                else discord.Color.red()
            )

            embed = discord.Embed(
                title=f"{status_emoji} General System Health", color=color
            )

            embed.add_field(name="Status", value=status.title(), inline=True)
            embed.add_field(name="Service", value=service, inline=True)
            embed.add_field(name="Version", value=version, inline=True)

            # Add component statuses
            if "components" in health_data:
                components = health_data["components"]
                for component_name, component_data in components.items():
                    comp_status = component_data.get("status", "unknown")
                    comp_emoji = "🟢" if comp_status == "healthy" else "🔴"
                    embed.add_field(
                        name=f"{component_name.title()}",
                        value=f"{comp_emoji} {comp_status.title()}",
                        inline=True,
                    )

            if "timestamp" in health_data:
                embed.set_footer(text=f"Checked at: {health_data['timestamp']}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except CustomException as e:
            await interaction.followup.send(
                f"❌ Failed to check general health: {str(e)}", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Unexpected error checking general health: {str(e)}", ephemeral=True
            )

    @health.command(
        name="test-trace", description="Test the observability tracing functionality."
    )
    @app_commands.describe()
    @discord_error_handler()
    async def test_trace(self, interaction: discord.Interaction):
        """Test observability tracing by sending a test trace."""
        await self._handle_test_trace(interaction)

    async def _handle_test_trace(self, interaction: discord.Interaction):
        """Handle observability trace test request."""
        try:
            await interaction.response.defer(ephemeral=True)

            async with self.api_client as client:
                test_result = await client.test_observability_trace()

            status = test_result.get("status", "unknown")
            message = test_result.get("message", "")
            trace_id = test_result.get("trace_id", "unknown")

            if status == "success":
                embed = discord.Embed(
                    title="🟢 Observability Trace Test",
                    description="✅ Trace test completed successfully",
                    color=discord.Color.green(),
                )

                embed.add_field(name="Status", value=status.title(), inline=True)
                embed.add_field(name="Trace ID", value=trace_id, inline=True)
                embed.add_field(name="Message", value=message, inline=False)

                # Add test data if available
                if "test_data" in test_result:
                    test_data = test_result["test_data"]
                    if "operations" in test_data:
                        operations = ", ".join(test_data["operations"])
                        embed.add_field(
                            name="Test Operations", value=operations, inline=False
                        )

                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="🔴 Observability Trace Test Failed",
                    color=discord.Color.red(),
                )

                embed.add_field(name="Status", value=status.title(), inline=True)
                embed.add_field(name="Message", value=message, inline=True)

                if "error" in test_result:
                    embed.add_field(
                        name="Error", value=test_result["error"], inline=False
                    )

                await interaction.followup.send(embed=embed, ephemeral=True)

        except CustomException as e:
            await interaction.followup.send(
                f"❌ Failed to test observability trace: {str(e)}", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Unexpected error testing observability trace: {str(e)}",
                ephemeral=True,
            )


async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(HealthCog(bot))
