import pytest

pytestmark = pytest.mark.asyncio


async def test_action_submit_success(mock_interaction, mock_action_cog):
    """Test successful action submission."""
    cog = mock_action_cog
    # Replace API client with mock
    cog.api_client.set_response_override(
        "submit_action",
        {
            "narrative": "You swing your sword and connect with the enemy!",
            "session_id": "test_session_123",
            "status": "success",
            "processing_time": 1.5,
            "correlation_id": "test-cid-123",
        },
    )

    interaction = mock_interaction

    await cog.submit.callback(cog, interaction, action="I attack the goblin")

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    # Check that embed was created with correct data
    call_args = interaction.followup.send.call_args
    embed = call_args.kwargs["embed"]

    assert embed.title == "🎭 AI Dungeon Master Response"
    assert "You swing your sword" in embed.description
    assert "Your Action" in embed.fields[0].name
    assert "I attack the goblin" in embed.fields[0].value


async def test_action_submit_error(mock_interaction, mock_action_cog):
    """Test action submission with API error."""
    cog = mock_action_cog
    # Replace API client with mock that raises exception
    cog.api_client.set_exception_override("submit_action", Exception("API Error"))

    interaction = mock_interaction

    await cog.submit.callback(cog, interaction, action="I attack the goblin")

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    # Check error message
    call_args = interaction.followup.send.call_args
    message = call_args.args[0]
    assert "Failed to submit action to AI DM" in message
    assert call_args.kwargs.get("ephemeral") is True


async def test_action_test_success(mock_interaction, mock_action_cog):
    """Test successful action API test."""
    cog = mock_action_cog
    # Replace API client with mock
    cog.api_client.set_response_override(
        "test_action_endpoint",
        {
            "status": "success",
            "message": "Action API is operational",
            "endpoint": "/api/action",
            "test_endpoint": "/api/action/test",
        },
    )

    interaction = mock_interaction

    await cog.test.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    call_args = interaction.followup.send.call_args
    embed = call_args.kwargs["embed"]

    assert embed.title == "🧪 Action API Test"
    assert "Status" in embed.fields[0].name
    assert "success" in embed.fields[0].value.lower()


async def test_action_session_info_with_session(mock_interaction, mock_action_cog):
    """Test action session info with active session."""
    cog = mock_action_cog
    # Set an active session
    cog._active_sessions[mock_interaction.guild_id] = "test_session_123"

    interaction = mock_interaction

    await cog.session_info.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    call_args = interaction.followup.send.call_args
    embed = call_args.kwargs["embed"]

    assert embed.title == "📊 Action Session Info"
    assert "test_session_123" in embed.description


async def test_action_session_info_no_session(mock_interaction, mock_action_cog):
    """Test action session info with no active session."""
    cog = mock_action_cog
    # Ensure no active session

    interaction = mock_interaction

    await cog.session_info.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    call_args = interaction.followup.send.call_args
    message = call_args.args[0]
    assert "No active action session found" in message


async def test_action_help_success(mock_interaction, mock_action_cog):
    """Test action help command."""
    cog = mock_action_cog

    interaction = mock_interaction

    await cog.help.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    call_args = interaction.followup.send.call_args
    embed = call_args.kwargs["embed"]

    assert embed.title == "🎭 AI Dungeon Master - Action Commands"
    assert "Submit Action" in embed.fields[0].name
    assert "Action Examples" in embed.fields[2].name


async def test_action_submit_with_custom_session(mock_interaction, mock_action_cog):
    """Test action submission with custom session ID."""
    cog = mock_action_cog
    cog.api_client.set_response_override(
        "submit_action",
        {
            "narrative": "You cast a powerful spell!",
            "session_id": "custom_session_456",
            "status": "success",
            "processing_time": 2.0,
            "correlation_id": "test-cid-456",
        },
    )

    interaction = mock_interaction

    await cog.submit.callback(
        cog, interaction, action="I cast fireball", session_id="custom_session_456"
    )

    # Verify the session was stored
    assert cog._active_sessions[interaction.guild_id] == "custom_session_456"


async def test_action_submit_with_campaign_context(mock_interaction, mock_action_cog):
    """Test action submission with campaign context."""
    cog = mock_action_cog
    cog.api_client.set_response_override(
        "submit_action",
        {
            "narrative": "You explore the ancient dungeon...",
            "session_id": "context_session_789",
            "status": "success",
            "processing_time": 1.8,
            "correlation_id": "test-cid-789",
        },
    )

    interaction = mock_interaction

    await cog.submit.callback(
        cog,
        interaction,
        action="I explore the dungeon",
        campaign_context="Forgotten Realms Campaign - Level 5",
    )

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()


async def test_cog_load(mock_action_cog):
    """Test cog load method."""
    cog = mock_action_cog

    # Should not raise any exceptions
    await cog.cog_load()
    assert True  # If we get here, the test passed


async def test_cog_unload(mock_action_cog):
    """Test cog unload method."""
    cog = mock_action_cog

    await cog.cog_unload()
    # MockApiClient doesn't have close method, so this just shouldn't raise an exception
    assert True


async def test_session_tracking(mock_interaction, mock_action_cog):
    """Test that sessions are properly tracked."""
    cog = mock_action_cog
    cog.api_client.set_response_override(
        "submit_action",
        {
            "narrative": "You defeat the enemy!",
            "session_id": "tracked_session_001",
            "status": "success",
            "processing_time": 1.2,
            "correlation_id": "test-cid-001",
        },
    )

    interaction = mock_interaction

    # Initially no session
    assert interaction.guild_id not in cog._active_sessions

    # Submit action with custom session ID
    await cog.submit.callback(
        cog, interaction, action="I defeat the enemy", session_id="tracked_session_001"
    )

    # Session should now be tracked
    assert cog._active_sessions[interaction.guild_id] == "tracked_session_001"


async def test_session_auto_generation(mock_interaction, mock_action_cog):
    """Test that sessions are auto-generated when not provided."""
    cog = mock_action_cog
    cog.api_client.set_response_override(
        "submit_action",
        {
            "narrative": "You explore the cave!",
            "session_id": "auto_generated_session",
            "status": "success",
            "processing_time": 1.0,
            "correlation_id": "test-cid-002",
        },
    )

    interaction = mock_interaction

    # Initially no session
    assert interaction.guild_id not in cog._active_sessions

    # Submit action without session_id (should auto-generate)
    await cog.submit.callback(cog, interaction, action="I explore the cave")

    # Session should be tracked (will be auto-generated by cog)
    assert interaction.guild_id in cog._active_sessions
    # The session ID will be auto-generated, so just verify it exists
    assert cog._active_sessions[interaction.guild_id] is not None
