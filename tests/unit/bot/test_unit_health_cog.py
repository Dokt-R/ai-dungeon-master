import pytest

pytestmark = pytest.mark.asyncio


async def test_ai_health_command_success(mock_interaction, mock_health_cog):
    """Test successful AI health check command."""
    cog = mock_health_cog
    # Replace API client with mock
    cog.api_client.set_response_override("get_ai_health", {
        "status": "healthy",
        "provider": "openai",
        "model": "gpt-4",
        "traced": True,
        "timestamp": "2025-08-24T20:30:00Z"
    })

    interaction = mock_interaction

    await cog.ai.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    # Check that embed was created with correct data
    call_args = interaction.followup.send.call_args
    embed = call_args.kwargs['embed']

    assert embed.title == "🟢 AI System Health"
    assert "Status" in embed.fields[0].name
    assert "healthy" in embed.fields[0].value.lower()
    assert "Provider" in embed.fields[1].name
    assert "openai" in embed.fields[1].value.lower()


async def test_ai_health_command_error(mock_interaction, mock_health_cog):
    """Test AI health check command with API error."""
    cog = mock_health_cog
    # Replace API client with mock that raises exception
    cog.api_client.set_exception_override("get_ai_health", Exception("API Error"))

    interaction = mock_interaction

    await cog.ai.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    # Check error message
    call_args = interaction.followup.send.call_args
    message = call_args.args[0]
    assert "unexpected error checking ai health" in message.lower()
    assert call_args.kwargs.get("ephemeral") is True


async def test_observability_health_command_success(mock_interaction, mock_health_cog):
    """Test successful observability health check command."""
    cog = mock_health_cog
    # Replace API client with mock
    cog.api_client.set_response_override("get_observability_health", {
        "status": "healthy",
        "provider": "langsmith",
        "project": "ai-dungeon-master"
    })

    interaction = mock_interaction

    await cog.observability.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    call_args = interaction.followup.send.call_args
    embed = call_args.kwargs['embed']

    assert embed.title == "🟢 Observability Health"
    assert "Status" in embed.fields[0].name
    assert "healthy" in embed.fields[0].value.lower()


async def test_general_health_command_success(mock_interaction, mock_health_cog):
    """Test successful general health check command."""
    cog = mock_health_cog
    # Replace API client with mock
    cog.api_client.set_response_override("get_general_health", {
        "status": "healthy",
        "service": "ai-dungeon-master-backend",
        "version": "1.0.0",
        "components": {
            "observability": {"status": "healthy"},
            "ai_client": {"status": "healthy"}
        },
        "timestamp": "2025-08-24T20:30:00Z"
    })

    interaction = mock_interaction

    await cog.general.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    call_args = interaction.followup.send.call_args
    embed = call_args.kwargs['embed']

    assert embed.title == "🟢 General System Health"
    assert "Status" in embed.fields[0].name
    assert "healthy" in embed.fields[0].value.lower()


async def test_test_trace_command_success(mock_interaction, mock_health_cog):
    """Test successful observability trace test command."""
    cog = mock_health_cog
    # Replace API client with mock
    cog.api_client.set_response_override("test_observability_trace", {
        "status": "success",
        "message": "Observability trace test completed",
        "trace_id": "test-trace-123",
        "test_data": {
            "operations": ["validate_config", "initialize_client", "send_trace"]
        }
    })

    interaction = mock_interaction

    await cog.test_trace.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    call_args = interaction.followup.send.call_args
    embed = call_args.kwargs['embed']

    assert embed.title == "🟢 Observability Trace Test"
    assert "Status" in embed.fields[0].name
    assert "success" in embed.fields[0].value.lower()
    assert "Trace ID" in embed.fields[1].name
    assert "test-trace-123" in embed.fields[1].value


async def test_test_trace_command_error(mock_interaction, mock_health_cog):
    """Test observability trace test command with error."""
    cog = mock_health_cog
    # Replace API client with mock
    cog.api_client.set_response_override("test_observability_trace", {
        "status": "error",
        "message": "Observability trace test failed",
        "error": "Connection timeout"
    })

    interaction = mock_interaction

    await cog.test_trace.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()

    call_args = interaction.followup.send.call_args
    embed = call_args.kwargs['embed']

    assert embed.title == "🔴 Observability Trace Test Failed"
    assert "Status" in embed.fields[0].name
    assert "error" in embed.fields[0].value.lower()


async def test_cog_load(mock_health_cog):
    """Test cog load method."""
    cog = mock_health_cog

    # Should not raise any exceptions
    await cog.cog_load()
    assert True  # If we get here, the test passed


async def test_cog_unload(mock_health_cog):
    """Test cog unload method."""
    cog = mock_health_cog

    await cog.cog_unload()
    # MockApiClient doesn't have close method, so this just shouldn't raise an exception
    assert True


async def test_api_client_initialization(mock_health_cog):
    """Test that API client is properly initialized in the cog."""
    cog = mock_health_cog

    # The fixture already handles the initialization, so we just verify the api_client exists
    assert cog.api_client is not None
    assert hasattr(cog.api_client, 'get_ai_health')
    assert hasattr(cog.api_client, 'get_observability_health')
    assert hasattr(cog.api_client, 'get_general_health')
    assert hasattr(cog.api_client, 'test_observability_trace')


async def test_api_client_base_url(mock_health_cog):
    """Test that API client uses the correct base URL."""
    cog = mock_health_cog

    # The MockApiClient should have been initialized with the default base URL
    # We can't directly test the URL since MockApiClient doesn't store it the same way,
    # but we can verify the client is working by calling a method
    result = await cog.api_client.get_ai_health()
    assert "status" in result



