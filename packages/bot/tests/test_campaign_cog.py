from discord.ext import commands
import pytest
import sys
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch
from packages.bot.cogs import campaign_cog

sys.modules["packages.backend.components.campaign_manager"] = mock.MagicMock()


@pytest.fixture
def bot():
    return MagicMock(spec=commands.Bot)


@pytest.fixture
def cog(bot):
    return campaign_cog.CampaignCog(bot)


@pytest.mark.asyncio
async def test_campaign_new_success(tmp_path, cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    interaction.response = AsyncMock()
    campaign_name = "test_campaign"
    # campaign_dir = tmp_path / "data" / "campaigns" / campaign_name

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "created successfully" in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_new_duplicate(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={
                "detail": "A campaign named 'existing_campaign' already exists."
            }
        )
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to create campaign"
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_new_permission_denied(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = False
    interaction.user.guild_permissions.manage_guild = False
    interaction.response = AsyncMock()
    campaign_name = "test_campaign"

    await cog._handle_campaign_new(interaction, campaign_name)
    interaction.response.send_message.assert_called_once()
    assert "do not have permission" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_new_backend_error(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    interaction.response = AsyncMock()
    campaign_name = "test_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("backend error")
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to create campaign"
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_join_success(cog):
    interaction = MagicMock()
    interaction.user.id = 789
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_join_nonexistent(cog):
    interaction = MagicMock()
    interaction.user.id = 789
    interaction.response = AsyncMock()
    campaign_name = "nonexistent_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={"detail": "No campaign named 'nonexistent_campaign' exists."}
        )
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to join campaign"
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_join_backend_error(cog):
    interaction = MagicMock()
    interaction.user.id = 789
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("backend error")
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to join campaign"
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_join_no_campaign_name_uses_last_active(cog):
    interaction = MagicMock()
    interaction.user.id = 1001
    interaction.response = AsyncMock()
    # Simulate backend returns success when no campaign_name is given (uses last_active_campaign)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, None)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_join_already_joined_fails(cog):
    interaction = MagicMock()
    interaction.user.id = 1002
    interaction.response = AsyncMock()
    campaign_name = "campaign1"
    # Simulate backend returns error for already joined
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={
                "detail": "Player is already joined to an active campaign on this server."
            }
        )
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "already joined" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_join_new_player_and_character(cog):
    interaction = MagicMock()
    interaction.user.id = 1003
    interaction.response = AsyncMock()
    campaign_name = "new_campaign"
    # Simulate backend returns success for new player/character
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_end_and_join_another(cog):
    interaction = MagicMock()
    interaction.user.id = 1004
    interaction.response = AsyncMock()
    campaign_name1 = "campaignA"
    campaign_name2 = "campaignB"
    # End campaignA
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_end(interaction, campaign_name1)
        interaction.response.send_message.assert_called_once()
        # Now join campaignB
        interaction.response.reset_mock()
        mock_post.return_value.status_code = 200
        await cog._handle_campaign_join(interaction, campaign_name2)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_join_no_last_active_campaign_fails(cog):
    interaction = MagicMock()
    interaction.user.id = 1005
    interaction.response = AsyncMock()
    # Simulate backend returns error for no last_active_campaign
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={
                "detail": "No campaign specified and no last active campaign found for player."
            }
        )
        await cog._handle_campaign_join(interaction, None)
        interaction.response.send_message.assert_called_once()
        assert (
            "no last active campaign"
            in interaction.response.send_message.call_args[0][0].lower()
        )


@pytest.mark.asyncio
async def test_campaign_join_new_character_linked(cog):
    interaction = MagicMock()
    interaction.user.id = 1006
    interaction.response = AsyncMock()
    campaign_name = "campaignC"
    # Simulate backend returns success for new character
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_continue_success_autosave(cog):
    interaction = MagicMock()
    interaction.user.id = 1111
    interaction.guild.id = 2222
    interaction.response = AsyncMock()
    # Simulate backend returns autosave
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = MagicMock(
            return_value={"campaign_name": "EpicQuest", "source": "autosave"}
        )
        await cog._handle_campaign_continue(interaction)
        interaction.response.send_message.assert_called_once()
        assert "autosave" in interaction.response.send_message.call_args[0][0].lower()
        assert (
            "resuming campaign"
            in interaction.response.send_message.call_args[0][0].lower()
        )


@pytest.mark.asyncio
async def test_campaign_party_formation_multiple_users_onboarding(cog):
    # User1 (admin/owner) creates the campaign
    interaction1 = MagicMock()
    interaction1.user.id = 3001
    interaction1.user.guild_permissions.administrator = True
    interaction1.user.guild_permissions.manage_guild = False
    interaction1.guild.id = 4001
    interaction1.response = AsyncMock()
    campaign_name = "party_campaign"

    # User2 (regular player) joins the campaign
    interaction2 = MagicMock()
    interaction2.user.id = 3002
    interaction2.user.guild_permissions.administrator = False
    interaction2.user.guild_permissions.manage_guild = False
    interaction2.guild.id = 4001
    interaction2.response = AsyncMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Campaign creation by user1
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_new(interaction1, campaign_name)
        interaction1.response.send_message.assert_called()
        interaction1.response.reset_mock()

        # User1 joins (should be auto-joined as creator, but test join logic)
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction1, campaign_name)
        interaction1.response.send_message.assert_called()
        interaction1.response.reset_mock()

        # User2 joins
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction2, campaign_name)
        interaction2.response.send_message.assert_called()
        msg2 = interaction2.response.send_message.call_args[0][0].lower()
        assert "joined campaign" in msg2 or "character" in msg2

        # Continue campaign (simulate party ready)
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = MagicMock(
            return_value={"campaign_name": campaign_name, "source": "save"}
        )
        await cog._handle_campaign_continue(interaction1)
        interaction1.response.send_message.assert_called_once()
        msg1 = interaction1.response.send_message.call_args[0][0].lower()
        assert "resuming campaign" in msg1
        assert "immersive role-playing mode" in msg1


@pytest.mark.asyncio
async def test_campaign_autosave_restore_after_onboarding_and_disconnect(cog):
    # User creates and joins a campaign (onboarding)
    interaction = MagicMock()
    interaction.user.id = 2222
    interaction.guild.id = 3333
    interaction.response = AsyncMock()
    campaign_name = "autosave_campaign"

    # Simulate successful campaign creation
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # First call: campaign creation
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called()
        interaction.response.reset_mock()

        # Second call: join campaign (onboarding)
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called()
        interaction.response.reset_mock()

        # Simulate disconnect (no-op)

        # Third call: continue campaign, backend returns autosave
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = MagicMock(
            return_value={"campaign_name": campaign_name, "source": "autosave"}
        )
        await cog._handle_campaign_continue(interaction)
        interaction.response.send_message.assert_called_once()
        msg = interaction.response.send_message.call_args[0][0].lower()
        assert "autosave" in msg
        assert "resuming campaign" in msg
        assert "entering immersive role-playing mode" in msg


@pytest.mark.asyncio
async def test_campaign_continue_success_save(cog):
    interaction = MagicMock()
    interaction.user.id = 1112
    interaction.guild.id = 2223
    interaction.response = AsyncMock()
    # Simulate backend returns last clean save
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = MagicMock(
            return_value={"campaign_name": "EpicQuest", "source": "save"}
        )
        await cog._handle_campaign_continue(interaction)
        interaction.response.send_message.assert_called_once()
        assert (
            "last clean save"
            in interaction.response.send_message.call_args[0][0].lower()
        )
        assert (
            "resuming campaign"
            in interaction.response.send_message.call_args[0][0].lower()
        )


@pytest.mark.asyncio
async def test_campaign_continue_backend_error(cog):
    interaction = MagicMock()
    interaction.user.id = 1113
    interaction.guild.id = 2224
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("backend error")
        await cog._handle_campaign_continue(interaction)
        interaction.response.send_message.assert_called_once()
        assert (
            "failed to continue campaign"
            in interaction.response.send_message.call_args[0][0].lower()
        )


@pytest.mark.asyncio
async def test_campaign_delete_with_active_characters(cog):
    # Admin creates and joins a campaign
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 5001
    interaction.guild.id = 6001
    interaction.channel.id = 7001
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    campaign_name = "active_char_campaign"

    # Simulate confirmation
    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch.object(cog.bot, "wait_for", new_callable=AsyncMock) as mock_wait_for,
    ):
        # First POST: placeholder (not used for logic)
        first_response = MagicMock()
        first_response.status_code = 200
        # Second POST: simulate campaign exists (400)
        second_response = MagicMock()
        second_response.status_code = 400
        second_response.json = AsyncMock(
            return_value={
                "detail": "Campaign has active characters and cannot be deleted."
            }
        )
        # Third POST: not reached if deletion is blocked

        mock_post.side_effect = [first_response, second_response]

        # Simulate user replies "yes"
        msg = MagicMock()
        msg.content = "yes"
        msg.author.id = 5001
        msg.channel.id = 7001
        mock_wait_for.return_value = msg

        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.response.send_message.assert_called()
        # Check that a generic failure message is sent with ephemeral=True
        found = False
        for call in interaction.followup.send.call_args_list:
            msg = str(call.args[0])
            kwargs = call.kwargs
            if msg.startswith("Failed to delete campaign") and kwargs.get(
                "ephemeral", False
            ):
                found = True
                break
        assert found, (
            "Expected generic failure message not found in followup.send calls"
        )


@pytest.mark.asyncio
async def test_campaign_continue_no_campaign(cog):
    interaction = MagicMock()
    interaction.user.id = 1114
    interaction.guild.id = 2225
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={
                "detail": "No campaign specified and no last active campaign found for player."
            }
        )
        await cog._handle_campaign_continue(interaction)
        interaction.response.send_message.assert_called_once()
        assert (
            "failed to continue campaign"
            in interaction.response.send_message.call_args[0][0].lower()
        )


# --- Tests for /campaign end ---


@pytest.mark.asyncio
async def test_campaign_end_success(cog):
    interaction = MagicMock()
    interaction.user.id = 2001
    interaction.guild.id = 3001
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        await cog._handle_campaign_end(interaction)
        interaction.response.send_message.assert_called_once()
        assert (
            "exiting immersive mode"
            in interaction.response.send_message.call_args[0][0].lower()
        )


@pytest.mark.asyncio
async def test_campaign_end_backend_error(cog):
    interaction = MagicMock()
    interaction.user.id = 2002
    interaction.guild.id = 3002
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("backend error")
        await cog._handle_campaign_end(interaction)
        interaction.response.send_message.assert_called_once()
        assert (
            "failed to exit campaign"
            in interaction.response.send_message.call_args[0][0].lower()
        )


@pytest.mark.asyncio
async def test_campaign_end_failure(cog):
    interaction = MagicMock()
    interaction.user.id = 2003
    interaction.guild.id = 3003
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={"detail": "Not in a campaign."}
        )
        await cog._handle_campaign_end(interaction)
        interaction.response.send_message.assert_called_once()
        assert (
            "failed to exit campaign"
            in interaction.response.send_message.call_args[0][0].lower()
        )


# --- Tests for /campaign delete ---


@pytest.mark.asyncio
async def test_campaign_delete_admin_confirms(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    interaction.channel.id = 789
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    campaign_name = "delete_me"

    # Simulate confirmation
    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch.object(cog.bot, "wait_for", new_callable=AsyncMock) as mock_wait_for,
    ):
        # First POST: placeholder (not used for logic)
        first_response = MagicMock()
        first_response.status_code = 200
        # Second POST: simulate campaign exists (400)
        second_response = MagicMock()
        second_response.status_code = 400
        second_response.json = AsyncMock(
            return_value={"detail": "A campaign named 'delete_me' already exists."}
        )
        # Third POST: simulate successful delete (200)
        third_response = MagicMock()
        third_response.status_code = 200

        mock_post.side_effect = [first_response, second_response, third_response]

        # Simulate user replies "yes"
        msg = MagicMock()
        msg.content = "yes"
        msg.author.id = 123
        msg.channel.id = 789
        mock_wait_for.return_value = msg

        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.response.send_message.assert_called()
        interaction.followup.send.assert_any_call(
            f"Campaign '{campaign_name}' deleted successfully.",
            ephemeral=False,
        )


@pytest.mark.asyncio
async def test_campaign_delete_cancelled(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    interaction.channel.id = 789
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    campaign_name = "delete_me"

    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch.object(cog.bot, "wait_for", new_callable=AsyncMock) as mock_wait_for,
    ):
        mock_post.return_value.status_code = 200
        msg = MagicMock()
        msg.content = "no"
        msg.author.id = 123
        msg.channel.id = 789
        mock_wait_for.return_value = msg

        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.followup.send.assert_any_call(
            "Campaign deletion cancelled.", ephemeral=True
        )


@pytest.mark.asyncio
async def test_campaign_delete_permission_denied(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = False
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    interaction.channel.id = 789
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    campaign_name = "delete_me"

    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch.object(cog.bot, "wait_for", new_callable=AsyncMock) as mock_wait_for,
    ):
        # Simulate confirmation
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={"detail": "Only the owner or admin can delete."}
        )
        msg = MagicMock()
        msg.content = "yes"
        msg.author.id = 123
        msg.channel.id = 789
        mock_wait_for.return_value = msg

        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.followup.send.assert_any_call(
            "You do not have permission to delete this campaign. (Only the owner or a server admin can delete.)",
            ephemeral=True,
        )
