from fastapi import APIRouter, Depends

from packages.backend.components.campaign_manager import CampaignManager
from packages.shared.models import (
    CampaignCreateRequest,
    CampaignDeleteRequest,
    CampaignStateRequest,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/create", summary="Create a new campaign")
async def create_campaign(
    req: CampaignCreateRequest, campaign_manager: CampaignManager = Depends()
):
    campaign = await campaign_manager.create_campaign(
        server_id=req.server_id,
        campaign_name=req.campaign_name,
        owner_id=req.owner_id,
    )
    return {
        "message": "Campaign created successfully.",
        "campaign_id": campaign.campaign_id,
    }


@router.delete("/delete", summary="Delete a campaign")
async def delete_campaign(
    req: CampaignDeleteRequest, campaign_manager: CampaignManager = Depends()
):
    await campaign_manager.delete_campaign(
        server_id=req.server_id,
        campaign_name=req.campaign_name,
        requester_id=req.requester_id,
        is_admin=req.is_admin,
    )
    return {"message": "Campaign deleted successfully."}


@router.get("/{campaign_id}/players", summary="List players in a campaign")
async def get_campaign_players(
    campaign_id: int, campaign_manager: CampaignManager = Depends()
):
    players = await campaign_manager.get_campaign_players(campaign_id)
    return [
        {"player_id": player.player_id, "username": player.username}
        for player in players
    ]


@router.get("/{server_id}/{campaign_name}", summary="Get campaign details")
async def get_campaign(
    server_id: str, campaign_name: str, campaign_manager: CampaignManager = Depends()
):
    campaign = await campaign_manager.get_campaign(server_id, campaign_name)
    # Return a dictionary instead of the Campaign object to avoid serialization issues
    return {
        "campaign_id": campaign.campaign_id,
        "server_id": campaign.server_id,
        "campaign_name": campaign.campaign_name,
        "owner_id": campaign.owner_id,
        "state": campaign.state,
    }


@router.put("/{campaign_id}/state", summary="Update campaign state")
async def update_campaign_state(
    campaign_id: int,
    req: CampaignStateRequest,
    campaign_manager: CampaignManager = Depends(),
):
    campaign = await campaign_manager.update_campaign_state(campaign_id, req.state)
    # Return a dictionary instead of the Campaign object to avoid serialization issues
    return {
        "campaign_id": campaign.campaign_id,
        "server_id": campaign.server_id,
        "campaign_name": campaign.campaign_name,
        "owner_id": campaign.owner_id,
        "state": campaign.state,
    }


#! ALL CODE BELOW THIS LINE IS A PLACEHOLDER AND SHOULD BE IGNORED UNLESS REQUESTED

# @router.post("/campaigns/kick", summary="Kick a player from the campaign")
# @fastapi_error_handler
# def kick_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/delete", summary="Delete a campaign")
# @fastapi_error_handler
# def delete_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign deleted successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/invite", summary="Invite a player to the campaign")
# @fastapi_error_handler
# def invite_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/leave", summary="Leave a campaign.")
# @fastapi_error_handler
# def remove_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? Could return players, assets, NPCs, lore, plot threads, story arcs, quests, locations
# @router.post("/campaigns/list", summary="List campaign information")
# @fastapi_error_handler
# def list_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/summary", summary="Exit a campaign")
# @fastapi_error_handler
# def summary_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/edit", summary="Exit a campaign")
# @fastapi_error_handler
# def edit_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? Start, end session. Potential get current session.
# @router.post("/campaigns/session", summary="Exit a campaign")
# @fastapi_error_handler
# def session_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? Park a campaign in case you want to hide it for the time being
# @router.post("/campaigns/archive", summary="Exit a campaign")
# @fastapi_error_handler
# def archive_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? States campaign name, players, permissions and important info
# @router.post(
#     "/campaigns/info",
#     summary="States campaign name, players, permissions and important info",
# )
# @fastapi_error_handler
# def info_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? Opens a list of current players and their permissions.
# @router.post(
#     "/campaigns/permissions",
#     summary="Opens a list of current players and their permissions.",
# )
# @fastapi_error_handler
# def permissions_campaign(req: ContinueCampaignRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }
