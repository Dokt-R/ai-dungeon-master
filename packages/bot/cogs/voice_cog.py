"""
Voice Cog for AI Dungeon Master Discord Bot.

This cog handles Discord voice channel integration, including joining/leaving channels,
voice state monitoring, permission checking, and voice activity detection.

Features:
- Voice channel joining and leaving
- Voice state change monitoring
- Permission validation
- Voice activity detection
- Connection error handling
- User interaction commands
"""

from datetime import datetime
from typing import Any, Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands

from packages.bot.services.voice_manager import voice_manager_service
from packages.shared.api_client import ApiClient
from packages.shared.logging_config import get_logger
from packages.shared.models import (
    VoiceChannelResponse,
)


class VoiceCog(commands.Cog):
    """
    Discord.py cog for voice channel management.

    Handles all voice-related Discord interactions and commands.
    """

    def __init__(self, bot: commands.Bot, api_base_url: str = "http://localhost:8000"):
        """Initialize the Voice Cog."""
        self.bot = bot
        self.logger = get_logger(f"{__name__}.VoiceCog")
        self.api_client = ApiClient(api_base_url)

        # Voice client tracking
        self._voice_clients: Dict[
            int, discord.VoiceClient
        ] = {}  # guild_id -> VoiceClient

        # Advanced voice session tracking
        self._voice_sessions: Dict[int, str] = {}  # guild_id -> session_id

        # Permission cache to reduce API calls
        self._permission_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timeout = 300  # 5 minutes

        self.logger.info("VoiceCog initialized")

    def _get_permission_cache_key(
        self, guild_id: str, channel_id: str, user_id: str
    ) -> str:
        """Generate a cache key for permissions."""
        return f"{guild_id}:{channel_id}:{user_id}"

    def _get_cached_permissions(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached permissions if still valid."""
        if cache_key not in self._permission_cache:
            return None

        cached_data = self._permission_cache[cache_key]
        if (
            datetime.utcnow().timestamp() - cached_data["timestamp"]
            > self._cache_timeout
        ):
            del self._permission_cache[cache_key]
            return None

        return cached_data["permissions"]

    def _cache_permissions(self, cache_key: str, permissions: Dict[str, Any]) -> None:
        """Cache permission data."""
        self._permission_cache[cache_key] = {
            "permissions": permissions,
            "timestamp": datetime.utcnow().timestamp(),
        }

    async def _check_voice_permissions(
        self,
        guild: discord.Guild,
        channel: discord.VoiceChannel,
        member: discord.Member,
    ) -> Dict[str, Any]:
        """
        Check voice permissions for a member in a voice channel.

        Args:
            guild: The Discord guild
            channel: The voice channel
            member: The guild member

        Returns:
            Dictionary with permission details
        """
        # Check cache first
        cache_key = self._get_permission_cache_key(
            str(guild.id), str(channel.id), str(member.id)
        )
        cached_perms = self._get_cached_permissions(cache_key)
        if cached_perms:
            return cached_perms

        # Calculate permissions
        permissions = channel.permissions_for(member)

        permission_data = {
            "can_connect": permissions.connect,
            "can_speak": permissions.speak,
            "can_mute_members": permissions.mute_members,
            "can_deafen_members": permissions.deafen_members,
            "can_move_members": permissions.move_members,
            "can_use_voice_activity": permissions.use_voice_activation,
            "can_priority_speaker": permissions.priority_speaker,
        }

        # Cache the results
        self._cache_permissions(cache_key, permission_data)

        return permission_data

    async def _get_channel_info(
        self, channel: discord.VoiceChannel
    ) -> VoiceChannelResponse:
        """Get detailed information about a voice channel."""
        # Check bot permissions
        bot_member = channel.guild.get_member(self.bot.user.id)
        if not bot_member:
            raise ValueError("Bot is not a member of the guild")

        bot_permissions = await self._check_voice_permissions(
            channel.guild, channel, bot_member
        )

        return VoiceChannelResponse(
            channel_id=str(channel.id),
            channel_name=channel.name,
            user_limit=channel.user_limit if channel.user_limit > 0 else None,
            bitrate=channel.bitrate,
            region=str(channel.rtc_region) if channel.rtc_region else "auto",
            member_count=len(channel.members),
            bot_can_join=bot_permissions["can_connect"],
            bot_permissions=bot_permissions,
        )

    @app_commands.command(name="voice_join", description="Join a voice channel")
    @app_commands.describe(channel="The voice channel to join")
    async def voice_join(
        self, interaction: discord.Interaction, channel: discord.VoiceChannel
    ) -> None:
        """
        Join a voice channel.

        Args:
            interaction: Discord interaction
            channel: Voice channel to join
        """
        try:
            await interaction.response.defer(ephemeral=True)

            # Check if bot is already in a voice channel in this guild
            if interaction.guild_id in self._voice_clients:
                existing_client = self._voice_clients[interaction.guild_id]
                if existing_client.is_connected():
                    await interaction.followup.send(
                        "I'm already connected to a voice channel in this server. "
                        "Use `/voice_leave` to disconnect first.",
                        ephemeral=True,
                    )
                    return

            # Check bot permissions
            channel_info = await self._get_channel_info(channel)
            if not channel_info.bot_can_join:
                await interaction.followup.send(
                    "I don't have permission to join that voice channel.",
                    ephemeral=True,
                )
                return

            # Check user permissions
            user_permissions = await self._check_voice_permissions(
                interaction.guild, channel, interaction.user
            )

            if not user_permissions["can_connect"]:
                await interaction.followup.send(
                    "You don't have permission to connect to that voice channel.",
                    ephemeral=True,
                )
                return

            # Start voice connection in service
            connection = await voice_manager_service.start_connection(
                guild_id=str(interaction.guild_id),
                channel_id=str(channel.id),
                user_id=str(interaction.user.id),
            )

            # Connect to Discord voice channel
            voice_client = await channel.connect()

            # Store voice client reference
            self._voice_clients[interaction.guild_id] = voice_client

            # Mark connection as complete
            await voice_manager_service.complete_connection(
                connection_id=connection.connection_id, user_id=str(interaction.user.id)
            )

            # Add the user as participant
            await voice_manager_service.add_participant(
                connection_id=connection.connection_id, user_id=str(interaction.user.id)
            )

            self.logger.info(
                "Joined voice channel",
                guild_id=interaction.guild_id,
                channel_id=channel.id,
                user_id=interaction.user.id,
                connection_id=connection.connection_id,
            )

            await interaction.followup.send(
                f"Successfully joined {channel.name}! 🎤", ephemeral=True
            )

        except Exception as e:
            self.logger.error(
                "Failed to join voice channel",
                error=str(e),
                guild_id=interaction.guild_id,
                channel_id=channel.id if "channel" in locals() else None,
                user_id=interaction.user.id,
            )

            error_message = "Failed to join voice channel"
            if "permission" in str(e).lower():
                error_message += ": Insufficient permissions"
            elif "already connected" in str(e).lower():
                error_message += ": Already connected to a voice channel"

            await interaction.followup.send(error_message, ephemeral=True)

    @app_commands.command(
        name="voice_leave", description="Leave the current voice channel"
    )
    async def voice_leave(self, interaction: discord.Interaction) -> None:
        """
        Leave the current voice channel.

        Args:
            interaction: Discord interaction
        """
        try:
            await interaction.response.defer(ephemeral=True)

            # Check if bot is in a voice channel
            if interaction.guild_id not in self._voice_clients:
                await interaction.followup.send(
                    "I'm not currently connected to a voice channel in this server.",
                    ephemeral=True,
                )
                return

            voice_client = self._voice_clients[interaction.guild_id]

            # Get connection info for cleanup
            connection = voice_manager_service.get_guild_connection(
                str(interaction.guild_id)
            )
            if connection:
                # Disconnect from service
                await voice_manager_service.disconnect_connection(
                    connection_id=connection.connection_id,
                    reason="user_request",
                    user_id=str(interaction.user.id),
                )

            # Disconnect from Discord
            await voice_client.disconnect()

            # Clean up voice client reference
            del self._voice_clients[interaction.guild_id]

            self.logger.info(
                "Left voice channel",
                guild_id=interaction.guild_id,
                user_id=interaction.user.id,
            )

            await interaction.followup.send(
                "Successfully left the voice channel! 👋", ephemeral=True
            )

        except Exception as e:
            self.logger.error(
                "Failed to leave voice channel",
                error=str(e),
                guild_id=interaction.guild_id,
                user_id=interaction.user.id,
            )

            await interaction.followup.send(
                "Failed to leave voice channel. Please try again.", ephemeral=True
            )

    @app_commands.command(
        name="voice_advanced_session",
        description="Create an advanced voice session with all features",
    )
    @app_commands.describe(
        focus_mode="Enable focus mode for priority speaker",
        focus_speaker="User to focus on (if focus mode enabled)",
    )
    async def voice_advanced_session(
        self,
        interaction: discord.Interaction,
        focus_mode: bool = False,
        focus_speaker: Optional[discord.Member] = None,
    ) -> None:
        """
        Create an advanced voice session with all features enabled.

        Args:
            interaction: Discord interaction
            focus_mode: Enable focus mode for priority speaker
            focus_speaker: User to focus on
        """
        try:
            await interaction.response.defer(ephemeral=True)

            # Check if bot is in a voice channel
            if interaction.guild_id not in self._voice_clients:
                await interaction.followup.send(
                    "I need to be in a voice channel first! Use `/voice_join` to connect.",
                    ephemeral=True,
                )
                return

            # Get current participants
            voice_client = self._voice_clients[interaction.guild_id]
            current_participants = [
                {
                    "source_id": str(member.id),
                    "user_id": str(member.id),
                    "volume": 1.0,
                    "priority": 5 if member.id == interaction.user.id else 3,
                }
                for member in voice_client.channel.members
                if not member.bot
            ]

            # Prepare session configuration
            session_config = {
                "focus_mode": focus_mode,
                "focus_speaker": str(focus_speaker.id)
                if focus_speaker and focus_mode
                else None,
                "sources": current_participants,
            }

            # Create advanced voice session
            session_id = f"advanced_{interaction.guild_id}_{interaction.user.id}"
            result = await self.api_client.create_voice_session(
                session_id, session_config
            )

            # Store session info
            self._voice_sessions[interaction.guild_id] = session_id

            embed = discord.Embed(
                title="🎵 Advanced Voice Session Started!",
                color=discord.Color.purple(),
                description=f"Session ID: `{session_id}`",
            )

            embed.add_field(
                name="🎯 Focus Mode",
                value="✅ Enabled" if focus_mode else "❌ Disabled",
                inline=True,
            )

            if focus_speaker and focus_mode:
                embed.add_field(
                    name="⭐ Focus Speaker",
                    value=focus_speaker.display_name,
                    inline=True,
                )

            embed.add_field(
                name="👥 Participants",
                value=str(len(current_participants)),
                inline=True,
            )

            embed.add_field(
                name="🎚️ Features Active",
                value="• 3D Spatial Audio\n• Speaker ID\n• Sentiment Analysis\n• Auto Mixing",
                inline=False,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error("Failed to create advanced voice session: %s", e)
            await interaction.followup.send(
                "Failed to start advanced voice session. Please try again.",
                ephemeral=True,
            )

    @app_commands.command(
        name="voice_session_status", description="Get advanced voice session status"
    )
    async def voice_session_status(self, interaction: discord.Interaction) -> None:
        """
        Get the status of the current advanced voice session.

        Args:
            interaction: Discord interaction
        """
        try:
            await interaction.response.defer(ephemeral=True)

            session_id = self._voice_sessions.get(interaction.guild_id)
            if not session_id:
                await interaction.followup.send(
                    "No advanced voice session is currently active.", ephemeral=True
                )
                return

            # Get session stats
            stats = await self.api_client.get_voice_session_stats(session_id)

            embed = discord.Embed(
                title="📊 Advanced Voice Session Status", color=discord.Color.blue()
            )

            embed.add_field(name="🔢 Session ID", value=session_id, inline=False)

            if "audio_mixing" in stats:
                mixing = stats["audio_mixing"]
                embed.add_field(
                    name="🎚️ Audio Mixing",
                    value=f"Active Sources: {mixing['active_sources']}\nMaster Volume: {mixing['master_volume']}\nFocus Mode: {'✅' if mixing['focus_mode'] else '❌'}",
                    inline=True,
                )

            if "conversation_intelligence" in stats:
                ci = stats["conversation_intelligence"]
                embed.add_field(
                    name="🧠 Conversation Intelligence",
                    value=f"Segments: {ci['total_segments']}\nActive Speakers: {ci['active_speakers']}",
                    inline=True,
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error("Failed to get voice session status: %s", e)
            await interaction.followup.send(
                "Failed to get session status. Please try again.", ephemeral=True
            )

    @app_commands.command(
        name="voice_spatial_position", description="Set spatial position for a user"
    )
    @app_commands.describe(
        user="User to position",
        x="Left (-) to Right (+) (-1.0 to 1.0)",
        y="Back (-) to Front (+) (-1.0 to 1.0)",
        z="Down (-) to Up (+) (-1.0 to 1.0)",
        distance="Distance from center (0.0 to 10.0)",
    )
    async def voice_spatial_position(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        distance: float = 1.0,
    ) -> None:
        """
        Set the 3D spatial position of a user in the voice session.

        Args:
            interaction: Discord interaction
            user: User to position
            x: Left/right position (-1.0 to 1.0)
            y: Back/front position (-1.0 to 1.0)
            z: Up/down position (-1.0 to 1.0)
            distance: Distance from center
        """
        try:
            await interaction.response.defer(ephemeral=True)

            session_id = self._voice_sessions.get(interaction.guild_id)
            if not session_id:
                await interaction.followup.send(
                    "No advanced voice session is currently active.", ephemeral=True
                )
                return

            # Set spatial position
            position = {
                "x": max(-1.0, min(1.0, x)),
                "y": max(-1.0, min(1.0, y)),
                "z": max(-1.0, min(1.0, z)),
                "distance": max(0.0, min(10.0, distance)),
            }

            await self.api_client.update_audio_source_position(
                session_id, str(user.id), position
            )

            embed = discord.Embed(
                title="🌌 Spatial Position Updated",
                color=discord.Color.green(),
                description=f"Updated position for {user.display_name}",
            )

            embed.add_field(
                name="📍 Position",
                value=f"X: {position['x']:.1f}, Y: {position['y']:.1f}, Z: {position['z']:.1f}",
                inline=True,
            )

            embed.add_field(
                name="📏 Distance", value=f"{position['distance']:.1f}m", inline=True
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error("Failed to update spatial position: %s", e)
            await interaction.followup.send(
                "Failed to update spatial position. Please try again.", ephemeral=True
            )

    @app_commands.command(
        name="voice_conversation_summary",
        description="Get conversation intelligence summary",
    )
    async def voice_conversation_summary(
        self, interaction: discord.Interaction
    ) -> None:
        """
        Get a summary of the current conversation intelligence analysis.

        Args:
            interaction: Discord interaction
        """
        try:
            await interaction.response.defer(ephemeral=True)

            session_id = self._voice_sessions.get(interaction.guild_id)
            if not session_id:
                await interaction.followup.send(
                    "No advanced voice session is currently active.", ephemeral=True
                )
                return

            # Get conversation summary
            summary = await self.api_client.get_conversation_summary(session_id)

            embed = discord.Embed(
                title="📝 Conversation Intelligence Summary", color=discord.Color.gold()
            )

            embed.add_field(
                name="⏱️ Duration",
                value=f"{summary.get('duration_minutes', 0):.1f} minutes",
                inline=True,
            )

            embed.add_field(
                name="🎤 Total Segments",
                value=str(summary.get("total_segments", 0)),
                inline=True,
            )

            embed.add_field(
                name="👥 Active Speakers",
                value=str(summary.get("active_speakers", 0)),
                inline=True,
            )

            if "average_engagement" in summary:
                embed.add_field(
                    name="🎭 Average Engagement",
                    value=f"{summary['average_engagement']:.2f}",
                    inline=True,
                )

            if "speaker_sentiment" in summary:
                sentiment_text = "\n".join(
                    [
                        f"{speaker}: {score:.2f}"
                        for speaker, score in summary["speaker_sentiment"].items()
                    ]
                )
                embed.add_field(
                    name="😊 Speaker Sentiment",
                    value=sentiment_text[:1024],  # Discord field limit
                    inline=False,
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error("Failed to get conversation summary: %s", e)
            await interaction.followup.send(
                "Failed to get conversation summary. Please try again.", ephemeral=True
            )

    @app_commands.command(
        name="voice_status", description="Get voice connection status"
    )
    async def voice_status(self, interaction: discord.Interaction) -> None:
        """
        Get the current voice connection status.

        Args:
            interaction: Discord interaction
        """
        try:
            await interaction.response.defer(ephemeral=True)

            status_response = voice_manager_service.get_connection_status(
                str(interaction.guild_id)
            )

            if not status_response or not status_response.connected:
                await interaction.followup.send(
                    "I'm not currently connected to a voice channel in this server.",
                    ephemeral=True,
                )
                return

            # Get channel info
            guild = interaction.guild
            channel = guild.get_channel(int(status_response.channel_id))

            embed = discord.Embed(
                title="Voice Connection Status", color=discord.Color.blue()
            )

            embed.add_field(
                name="Channel",
                value=channel.name if channel else "Unknown",
                inline=True,
            )

            embed.add_field(
                name="Participants",
                value=str(status_response.participant_count),
                inline=True,
            )

            if status_response.connected_at:
                duration = datetime.utcnow() - status_response.connected_at
                embed.add_field(
                    name="Connected For",
                    value=f"{duration.seconds // 60} minutes",
                    inline=True,
                )

            if status_response.participants:
                participant_names = []
                for participant_id in status_response.participants[:5]:  # Limit to 5
                    member = guild.get_member(int(participant_id))
                    if member:
                        participant_names.append(member.display_name)
                if participant_names:
                    embed.add_field(
                        name="Current Participants",
                        value="\n".join(participant_names),
                        inline=False,
                    )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(
                "Failed to get voice status",
                error=str(e),
                guild_id=interaction.guild_id,
                user_id=interaction.user.id,
            )

            await interaction.followup.send(
                "Failed to get voice status. Please try again.", ephemeral=True
            )

    @app_commands.command(
        name="voice_info", description="Get information about a voice channel"
    )
    @app_commands.describe(channel="The voice channel to get info about")
    async def voice_info(
        self, interaction: discord.Interaction, channel: discord.VoiceChannel
    ) -> None:
        """
        Get information about a voice channel.

        Args:
            interaction: Discord interaction
            channel: Voice channel to get info about
        """
        try:
            await interaction.response.defer(ephemeral=True)

            channel_info = await self._get_channel_info(channel)

            embed = discord.Embed(
                title=f"Voice Channel: {channel_info.channel_name}",
                color=discord.Color.green(),
            )

            embed.add_field(
                name="Channel ID", value=channel_info.channel_id, inline=True
            )

            embed.add_field(
                name="Bitrate", value=f"{channel_info.bitrate // 1000}kbps", inline=True
            )

            embed.add_field(name="Region", value=channel_info.region, inline=True)

            if channel_info.user_limit:
                embed.add_field(
                    name="User Limit", value=str(channel_info.user_limit), inline=True
                )

            embed.add_field(
                name="Members", value=str(channel_info.member_count), inline=True
            )

            embed.add_field(
                name="Bot Can Join",
                value="✅ Yes" if channel_info.bot_can_join else "❌ No",
                inline=True,
            )

            if not channel_info.bot_can_join and channel_info.bot_permissions:
                missing_perms = [
                    perm
                    for perm, has_perm in channel_info.bot_permissions.items()
                    if not has_perm and perm != "can_priority_speaker"
                ]
                if missing_perms:
                    embed.add_field(
                        name="Missing Permissions",
                        value="\n".join(missing_perms),
                        inline=False,
                    )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(
                "Failed to get voice channel info",
                error=str(e),
                guild_id=interaction.guild_id,
                channel_id=channel.id if "channel" in locals() else None,
                user_id=interaction.user.id,
            )

            await interaction.followup.send(
                "Failed to get voice channel information. Please try again.",
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """
        Handle voice state updates.

        Args:
            member: The member whose voice state changed
            before: Voice state before the change
            after: Voice state after the change
        """
        try:
            # Ignore bot's own voice state changes
            if member.id == self.bot.user.id:
                return

            guild_id = str(member.guild.id)
            user_id = str(member.id)

            # Get current connection for this guild
            connection = voice_manager_service.get_guild_connection(guild_id)
            if not connection:
                return

            # Handle user joining voice channel
            if before.channel is None and after.channel is not None:
                # User joined a voice channel
                if str(after.channel.id) == connection.channel_id:
                    # User joined our voice channel
                    await voice_manager_service.add_participant(
                        connection_id=connection.connection_id, user_id=user_id
                    )
                    self.logger.info(
                        "User joined voice channel",
                        guild_id=guild_id,
                        channel_id=connection.channel_id,
                        user_id=user_id,
                    )

            # Handle user leaving voice channel
            elif before.channel is not None and after.channel is None:
                # User left a voice channel
                if str(before.channel.id) == connection.channel_id:
                    # User left our voice channel
                    await voice_manager_service.remove_participant(
                        connection_id=connection.connection_id, user_id=user_id
                    )
                    self.logger.info(
                        "User left voice channel",
                        guild_id=guild_id,
                        channel_id=connection.channel_id,
                        user_id=user_id,
                    )

            # Handle user switching channels
            elif (
                before.channel is not None
                and after.channel is not None
                and before.channel.id != after.channel.id
            ):
                # User switched channels
                if str(before.channel.id) == connection.channel_id:
                    # User left our voice channel
                    await voice_manager_service.remove_participant(
                        connection_id=connection.connection_id, user_id=user_id
                    )
                    self.logger.info(
                        "User switched out of voice channel",
                        guild_id=guild_id,
                        channel_id=connection.channel_id,
                        user_id=user_id,
                    )

                elif str(after.channel.id) == connection.channel_id:
                    # User joined our voice channel
                    await voice_manager_service.add_participant(
                        connection_id=connection.connection_id, user_id=user_id
                    )
                    self.logger.info(
                        "User switched into voice channel",
                        guild_id=guild_id,
                        channel_id=connection.channel_id,
                        user_id=user_id,
                    )

        except Exception as e:
            self.logger.error(
                "Error handling voice state update",
                error=str(e),
                guild_id=member.guild.id,
                user_id=member.id,
            )

    @commands.Cog.listener()
    async def on_voice_client_error(
        self, voice_client: discord.VoiceClient, error: Exception
    ) -> None:
        """
        Handle voice client errors.

        Args:
            voice_client: The voice client that encountered an error
            error: The exception that occurred
        """
        try:
            guild_id = str(voice_client.guild.id)

            # Get connection for this guild
            connection = voice_manager_service.get_guild_connection(guild_id)
            if connection:
                # Handle the error through the service
                await voice_manager_service.handle_connection_error(
                    connection_id=connection.connection_id,
                    error=str(error),
                    user_id="discord_voice_client",
                )

                self.logger.error(
                    "Voice client error handled",
                    guild_id=guild_id,
                    connection_id=connection.connection_id,
                    error=str(error),
                )

        except Exception as e:
            self.logger.error(
                "Error handling voice client error",
                error=str(e),
                original_error=str(error),
            )

    async def cog_unload(self) -> None:
        """Clean up when cog is unloaded."""
        try:
            # Clean up advanced voice sessions
            for guild_id, session_id in self._voice_sessions.items():
                try:
                    await self.api_client.cleanup_voice_session(session_id)
                except Exception as e:
                    self.logger.error(
                        "Error cleaning up advanced voice session",
                        guild_id=guild_id,
                        session_id=session_id,
                        error=str(e),
                    )

            # Clear session tracking
            self._voice_sessions.clear()

            # Disconnect from all voice channels
            for guild_id, voice_client in self._voice_clients.items():
                try:
                    if voice_client.is_connected():
                        await voice_client.disconnect()

                    # Clean up service connection
                    connection = voice_manager_service.get_guild_connection(
                        str(guild_id)
                    )
                    if connection:
                        await voice_manager_service.disconnect_connection(
                            connection_id=connection.connection_id,
                            reason="cog_unload",
                            user_id="system",
                        )

                except Exception as e:
                    self.logger.error(
                        "Error disconnecting voice client during unload",
                        guild_id=guild_id,
                        error=str(e),
                    )

            # Clear voice clients
            self._voice_clients.clear()

            # Close API client
            try:
                await self.api_client.close()
            except Exception as e:
                self.logger.error("Error closing API client", error=str(e))

            self.logger.info("VoiceCog unloaded successfully")

        except Exception as e:
            self.logger.error("Error during VoiceCog unload", error=str(e))


async def setup(bot: commands.Bot) -> None:
    """Setup function for the voice cog."""
    await bot.add_cog(VoiceCog(bot))
